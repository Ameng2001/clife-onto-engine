"""Action 执行内核 —— 整个本体层的"心脏"。与行业无关。

固定流水线（见 docs §3）：
  1. guard 前置校验      declarative：参数 + 用户上下文 + 角色
  2. validate 预演（可选）无副作用，返回预估，不落库
  3. 内存变更            handler 暂存写入 → live index（写即可见）
  4. 写后规则校验        post_rules：declarative + function（查图谱），收集全部不短路
  5a. 全部通过           commit + 审计快照 + HIL 路由 + 副作用编排
  5b. 任一 hard 违反     确定性回滚 + 结构化拒绝

三条铁律：规则写入后校验 · 多规则不短路 · 拒绝是结构化数据。
"""
from __future__ import annotations

from typing import Optional

from ..metamodel import ActionDef, Backing, RuleDef, Severity
from ..query import GraphStore, InMemoryStore, QueryView, StagedLink, StagedWrite
from ..sdk.capability import Capability
from ..sdk.context import Actor, ActionContext
from ..sdk.registry import Registry
from ..trust.audit import AuditSnapshot, AuditStore, RuleEvaluation
from ..trust.confidence import ConfidenceBus
from .rejection import (
    ActionPreview,
    ActionResult,
    StructuredRejection,
    Violation,
)


class ActionEngine:
    def __init__(
        self,
        registry: Registry,
        store: Optional[GraphStore] = None,
        audit: Optional[AuditStore] = None,
    ) -> None:
        self.registry = registry
        self.store = store or InMemoryStore()
        self.audit = audit or AuditStore()

    # 公开入口 ------------------------------------------------------------
    def execute(
        self,
        ontology_id: str,
        action_name: str,
        params: dict,
        actor: Actor,
        *,
        schema_version: str = "unknown",
        ts: Optional[str] = None,
    ):
        spec = self.registry.get_action(ontology_id, action_name)
        ctx, cap, overlay = self._new_ctx(spec, params, actor)

        # 1. guard（declarative，写入前）
        guard_violations = self._eval_rules(spec.guards, cap, ontology_id)
        if any(v.severity == Severity.HARD.value for v in guard_violations):
            rej = StructuredRejection(
                ontology_id=ontology_id, action=action_name, phase="guard",
                violations=tuple(guard_violations),
                state_snapshot=self._snapshot(ctx),
                diagnosis="guard 前置校验未过（参数/权限）",
            )
            self._audit(spec, ctx, guard_violations, "rejected", schema_version, ts)
            return rej

        # 3. 内存变更：handler 经 Capability 暂存写入 overlay（live index，写即可见）
        if spec.impl is not None:
            spec.impl(cap)

        # 4. 写后规则校验：收集全部，不短路
        post_violations = self._eval_rules(spec.post_rules, cap, ontology_id)
        touched_hard = any(v.severity == Severity.HARD.value for v in post_violations)

        if touched_hard:
            # 5b. 确定性回滚（丢弃 overlay）+ 结构化拒绝
            overlay.clear()
            rej = StructuredRejection(
                ontology_id=ontology_id, action=action_name, phase="post_write",
                violations=tuple(post_violations),
                state_snapshot=self._snapshot(ctx),
                diagnosis=ConfidenceBus.diagnose_rejection(ctx.confidence),
            )
            self._audit(spec, ctx, post_violations, "rejected", schema_version, ts)
            return rej

        # 5a. commit：flush overlay 到基底 + 审计 + HIL + 副作用
        hil_required = ConfidenceBus.should_route_hil(spec.hil, ctx.confidence, touched_hard)
        decision = "pending_hil" if hil_required else "committed"
        self._flush(ctx)
        self._audit(spec, ctx, post_violations, decision, schema_version, ts)
        scheduled = tuple(e.type for e in ctx.effects) if not hil_required else ()

        return ActionResult(
            ontology_id=ontology_id, action=action_name, decision=decision,
            written=tuple((w.object_type, w.key) for w in ctx.changeset if isinstance(w, StagedWrite)),
            effects_scheduled=scheduled, confidence=ctx.confidence,
            hil_required=hil_required,
            advisory=tuple(v for v in post_violations if v.severity == Severity.SOFT.value),
        )

    def validate(self, ontology_id: str, action_name: str, params: dict, actor: Actor) -> ActionPreview:
        """2. 预演：跑 guard + handler 暂存 + 写后校验，但**永不落库**。"""
        spec = self.registry.get_action(ontology_id, action_name)
        if not spec.validate_supported:
            raise ValueError(f"Action {ontology_id}.{action_name} 不支持 validate 预演")
        ctx, cap, overlay = self._new_ctx(spec, params, actor)
        violations = list(self._eval_rules(spec.guards, cap, ontology_id))
        if spec.impl is not None:
            spec.impl(cap)
        violations += self._eval_rules(spec.post_rules, cap, ontology_id)
        staged = tuple((w.object_type, w.key) for w in ctx.changeset if isinstance(w, StagedWrite))  # 先快照
        overlay.clear()  # 预演无副作用
        would_commit = not any(v.severity == Severity.HARD.value for v in violations)
        return ActionPreview(
            ontology_id=ontology_id, action=action_name, would_commit=would_commit,
            staged=staged, violations=tuple(violations), confidence=ctx.confidence,
        )

    # 内部 ----------------------------------------------------------------
    def _new_ctx(self, spec: ActionDef, params: dict, actor: Actor):
        overlay: list = []
        view = QueryView(self.store, overlay)
        ctx = ActionContext(
            ontology_id=spec.namespace, params=params, actor=actor, view=view, overlay=overlay,
        )
        cap = Capability(ctx, self.registry, action_def=spec)
        return ctx, cap, overlay

    def _eval_rules(self, names, cap: Capability, ontology_id: str) -> list[Violation]:
        out: list[Violation] = []
        for name in names:
            rule = self.registry.get_rule(ontology_id, name)
            res = rule.impl(cap) if rule.impl is not None else _RulePass()
            if not res.passed:
                out.append(Violation(
                    rule=name, severity=rule.severity.value, backing=rule.backing.value,
                    message=res.message or rule.message_template,
                    suggestion=getattr(res, "suggestion", "") or "",
                ))
        return out

    def _flush(self, ctx: ActionContext) -> None:
        for op in ctx.changeset:
            if isinstance(op, StagedLink):
                self.store.put_link(op)
            else:
                self.store.put_object(op.object_type, op.key, op.data)

    def _snapshot(self, ctx: ActionContext) -> dict:
        return {"params": dict(ctx.params), "actor": {"id": ctx.actor.id, "role": ctx.actor.role}}

    def _audit(self, spec: ActionDef, ctx: ActionContext, violations, decision, schema_version, ts) -> None:
        evals = tuple(
            RuleEvaluation(rule=v.rule, result="violate", backing=v.backing,
                           severity=v.severity, message=v.message)
            for v in violations
        )
        self.audit.record(AuditSnapshot(
            ontology_id=spec.namespace, action=spec.name,
            actor_id=ctx.actor.id, actor_role=ctx.actor.role,
            inputs_snapshot=self._snapshot(ctx), rules_evaluated=evals,
            decision=decision, confidence=ctx.confidence,
            evidence=tuple(ctx.evidence), schema_version=schema_version, ts=ts,
        ))


class _RulePass:
    passed = True
    message = ""
    suggestion = ""
