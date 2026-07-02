"""草业文档语料（RAG · advise 通道的检索源）—— 标准/案例全文摘录。

供开放问答检索、每段带出处；**只读、不驱动写入**。生产替换为向量库对全文分块的检索
（同 KnowledgeRetriever 协议），此处的离线 InMemoryRetriever 语料仅供脱网 demo / CI。
不参与 SPI 注册（纯数据），由调用方按需构造 retriever，故不在 __init__ import。
"""
from clife_onto_engine.retrieval import DocChunk

CHUNKS = (
    DocChunk("std_gbt37067_1",
             "退化草地修复应优先选用乡土草种，按立地类型（沙地/盐碱/矿山/边坡）匹配适生草种，混播比例合计应为100%。",
             source="GB/T 37067 退化草地修复技术规范", refs=("GB/T 37067",)),
    DocChunk("case_盐碱_001",
             "巴彦淖尔某重度盐渍化地块采用碱茅为主、星星草为辅的混播组合，配丸粒化与微生物菌剂，三年盖度显著回升。",
             source="修复案例 case_盐碱_001", refs=("DB15/T",)),
    DocChunk("std_nyt1574_1",
             "苜蓿干草按相对饲用价值 RFV 分级：特级≥151，一级125–150，二级103–124，三级87–102，等外<87。",
             source="NY/T 1574 苜蓿干草质量分级", refs=("NY/T 1574",)),
    DocChunk("std_gb13078_1",
             "霉变饲草（霉菌毒素超出卫生限量）判为不合格，不得进入交易、销售与饲喂。",
             source="GB 13078 饲料卫生标准", refs=("GB 13078",)),
    DocChunk("play_window_1",
             "盐碱地补播最佳窗口为春季返青前后与雨季前；喷播适坡面大面积，补播适轻度退化。",
             source="修复施工窗口手册", refs=("DB15/T",)),
)
