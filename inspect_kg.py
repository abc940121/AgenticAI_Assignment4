"""Check for graduate 70 passing score."""
from neo4j import GraphDatabase
d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
s = d.session()

# Search all articles mentioning 70
print("=== Articles containing '70' ===")
for r in s.run("MATCH (a:Article) WHERE a.content CONTAINS '70' RETURN a.number AS num, a.reg_name AS reg"):
    print(r.data())

# Get Article 17 full content
print("\n=== Article 17 full ===")
r = s.run("MATCH (a:Article {number: 'Article 17', reg_name: 'NCU General Regulations'}) RETURN a.content AS c").single()
if r:
    safe = r["c"].encode("ascii", errors="replace").decode("ascii")
    print(safe)

# Get Article 59 full content  
print("\n=== Article 59 full ===")
r = s.run("MATCH (a:Article {number: 'Article 59', reg_name: 'NCU General Regulations'}) RETURN a.content AS c").single()
if r:
    safe = r["c"].encode("ascii", errors="replace").decode("ascii")
    print(safe)

# Search for "military" to check Q13
print("\n=== Military training ===")
for r in s.run("MATCH (a:Article) WHERE a.content CONTAINS 'Military' OR a.content CONTAINS 'military' RETURN a.number AS num, a.reg_name AS reg, substring(a.content, 0, 200) AS c"):
    data = r.data()
    print(f"--- {data['reg']} - {data['num']}: {data['c'][:200]}")

d.close()
