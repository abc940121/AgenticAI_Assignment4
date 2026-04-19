from neo4j import GraphDatabase
d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
s = d.session()

queries = [
    "fee OR replacing OR lost OR easycard OR student",
    "fee AND replacing AND lost AND easycard AND student",
    "fee replacing lost easycard student"
]

for q in queries:
    print(f"\nQuery: {q}")
    for r in s.run("CALL db.index.fulltext.queryNodes('article_content_idx', $q) YIELD node, score RETURN node.number AS num, node.reg_name AS reg, score LIMIT 5", q=q):
        print(f"  {r['reg']} - {r['num']}: {r['score']}")

d.close()
