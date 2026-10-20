import json
from roomloop.store import get_conn, init_db
from roomloop.core import create_single, create_recurring

DB = "roomloop.db"
data = json.load(open("test_data.json"))
c = get_conn(DB)
init_db(c)
c.execute("DELETE FROM bookings"); c.execute("DELETE FROM rooms"); c.commit()
for r in data["rooms"]:
    c.execute("INSERT INTO rooms VALUES (?,?,?)",
              (r["id"], r["name"], r["capacity"]))
c.commit()
for b in data["singles"]:
    row = create_single(c, b["room_id"], b["start"], b["end"], b["user"],
                        b["timezone"])
    print("seeded single id:", row["id"], "room", b["room_id"])
for b in data["recurring"]:
    res = create_recurring(c, b["room_id"], b["start"], b["end"], b["user"],
                           b["repeat_until"], b["timezone"])
    print("seeded series:", res["series_id"], len(res["rows"]), "created")
c.close()
print("done ->", DB)
