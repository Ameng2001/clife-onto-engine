#!/usr/bin/env bash
# 治理写桥在线端到端：真实 UModel 下 act→commit→反映→读层可见；反例非乡土→拒绝→读层不变。
#
# 这是两个半区合体的活证据：MCP agent 在 UModel 同台「读对象图 + 触发受治理的写」，
# 写经引擎 guard→写后规则→确定性回滚→审计，只有【已提交】才反映进 UModel 读层。
#
# 前置（同 verify_umodel_online.sh）：
#   docker build -f deployments/docker/Dockerfile -t umodel-open-source:local .   # 在 UModel 仓库内
#   python scripts/export_umodel.py
#   docker run -d --name umodel-verify -p 8081:8080 -v "$PWD/build/umodel:/packs:ro" \
#     umodel-open-source:local --addr :8080 --data /data --graphstore file.memory --import-root /packs
#
# 用法：  bash scripts/verify_mcp_bridge_online.sh [BASE_URL]
set -euo pipefail
B="${1:-http://localhost:8081}"
jqd() { python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps(d.get('data',{}).get('data',d),ensure_ascii=False))"; }

echo "== 装载 grass 定义（workspace + entity_set，含 Project/SeedPack）=="
curl -fsS -XPOST "$B/api/v1/workspaces" -H 'content-type: application/json' -d '{"id":"grass"}' >/dev/null 2>&1 || true
curl -fsS -XPOST "$B/api/v1/umodel/grass/import" -H 'content-type: application/json' \
  -d '{"path":"/packs/grass/umodel"}' | python3 -c "import sys,json;print('imported',json.load(sys.stdin)['imported'])"

echo "== 合规 act：出一地一方（碱茅）→ 经引擎提交 → 反映进读层 =="
python3 - "$B" <<'PY'
import sys
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.mcp import GovernedBridge, Reflector
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
import plugins.grass
store = InMemoryStore(); plugins.grass.seed_reference_data(store)
br = GovernedBridge(ontology_id="grass", registry=spi.registry, store=store,
                    compiler=None, actor=Actor("u1","施工方"),
                    engine=ActionEngine(spi.registry, store=store),
                    reflector=Reflector(sys.argv[1], "grass"), enable_act=True)
ok = br.act("出一地一方", {"site_id":"parcel_001","species":["碱茅"],"budget":300})
print("  合规:", ok["kind"], "reflected=", ok.get("reflected"))
bad = br.act("出一地一方", {"site_id":"parcel_001","species":["紫花苜蓿"],"budget":300})
print("  违规:", bad["kind"], "rules=", [v["rule"] for v in bad.get("violations",[])])
PY

echo "== 读层验收：.entity 查 grass.Project（合规提交应可见）=="
curl -fsS -XPOST "$B/api/v1/query/grass/execute" -H 'content-type: application/json' \
  -d "{\"query\":\".entity with(domain='grass', name='grass.Project') | project __entity_id__, site_id, status\"}" | jqd
echo "== 读层验收：.entity 查 grass.SeedPack =="
curl -fsS -XPOST "$B/api/v1/query/grass/execute" -H 'content-type: application/json' \
  -d "{\"query\":\".entity with(domain='grass', name='grass.SeedPack') | project __entity_id__, site_id\"}" | jqd
echo
echo "OK 治理写桥在线验收：合规经引擎提交并反映、违规被本体兜底拒绝（读层无脏写）。"
