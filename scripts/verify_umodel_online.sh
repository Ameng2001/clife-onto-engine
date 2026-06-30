#!/usr/bin/env bash
# UModel 在线权威验收：把导出的 pack 装进真实 umodel-server，跑 SPL 查询确认对象图可读。
#
# 这是 docs/04-umodel-interop.md 的「在线权威校验」路径（区别于离线 smoke_umodel.py）：
# import / entities:write / relations:write 全部经真实 UModel 校验，再用 .umodel/.entity/.topo 验收。
#
# 前置：
#   1) 一次性从上游构建镜像（深度使用协议下取 alibaba/UnifiedModel）：
#        docker build -f deployments/docker/Dockerfile -t umodel-open-source:local .
#   2) 导出 pack：python scripts/export_umodel.py
#   3) 起 server（挂载导出目录、import-root 限定到挂载点）：
#        docker run -d --name umodel-verify -p 8081:8080 \
#          -v "$PWD/build/umodel:/packs:ro" umodel-open-source:local \
#          --addr :8080 --data /data --graphstore file.memory --import-root /packs
#
# 用法：  bash scripts/verify_umodel_online.sh [BASE_URL] [ONTOLOGY]
set -euo pipefail
B="${1:-http://localhost:8081}"
NS="${2:-grass}"
PACK="build/umodel/$NS"
jqd() { python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps(d.get('data',{}).get('data',d),ensure_ascii=False))"; }

echo "== health =="; curl -fsS "$B/healthz"; echo
echo "== create workspace $NS =="
curl -fsS -XPOST "$B/api/v1/workspaces" -H 'content-type: application/json' -d "{\"id\":\"$NS\"}" >/dev/null && echo ok
echo "== import umodel defs（权威校验 entity_set/link/storage）=="
curl -fsS -XPOST "$B/api/v1/umodel/$NS/import" -H 'content-type: application/json' \
  -d "{\"path\":\"/packs/$NS/umodel\"}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('imported',d['imported'],'skipped',d['skipped'])"
echo "== write entities（权威校验 __entity_id__ 32-hex / 观测时间）=="
python3 -c "import json;print(json.dumps({'entities':json.load(open('$PACK/sample-data/entities.json'))}))" \
  | curl -fsS -XPOST "$B/api/v1/entitystore/$NS/entities:write" -H 'content-type: application/json' -d @- \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('accepted',d['accepted'],'failed',d['failed'])"
echo "== write relations =="
python3 -c "import json;print(json.dumps({'relations':json.load(open('$PACK/sample-data/relations.json'))}))" \
  | curl -fsS -XPOST "$B/api/v1/entitystore/$NS/relations:write" -H 'content-type: application/json' -d @- \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('accepted',d['accepted'],'failed',d['failed'])"
echo "== SPL .umodel：列出 entity_set =="
curl -fsS -XPOST "$B/api/v1/query/$NS/execute" -H 'content-type: application/json' \
  -d "{\"query\":\".umodel with(kind='entity_set') | project domain, name\"}" | jqd
echo "== SPL .topo：cypher 遍历关系 =="
curl -fsS -XPOST "$B/api/v1/query/$NS/execute" -H 'content-type: application/json' \
  -d "{\"query\":\".topo | graph-call cypher(\`MATCH (s)-[r]->(d) RETURN r.__relation_type__\`)\"}" | jqd
echo
echo "OK UModel 在线验收通过：pack 被真实 UModel 接受，对象图可经 SPL 读取。浏览 ${B}"
