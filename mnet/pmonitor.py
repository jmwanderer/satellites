import os
import sys
import sqlite3
import shutil
import time


def open_db(file_path: str):
    db = sqlite3.connect(file_path)
    return db

def create_db(file_path: str):
    data_dir = os.path.dirname(file_path)
    if len(data_dir) > 0 and not os.path.exists(data_dir):
        os.makedirs(data_dir)

    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    db = sqlite3.connect(file_path)
    with open(path) as f:
        db.executescript(f.read())
    db.close()
 
def is_running(db, address: str) -> bool:
    c = db.cursor()
    q = c.execute("SELECT running FROM targets WHERE address = ?", (address,))
    entry = q.fetchone();
    return entry[0]


def set_running(db, address: str, running: bool):
    c = db.cursor()
    q = c.execute("UPDATE targets SET running = ? WHERE address = ?", 
                  (running, address,))
    db.commit()

def can_run(db, address: str) -> bool:
    c = db.cursor()
    q = c.execute("SELECT run FROM targets WHERE address = ?", (address,))
    entry = q.fetchone();
    return entry[0]

def set_can_run(db, address: str, can_run):
    c = db.cursor()
    q = c.execute("UPDATE targets SET run = ? WHERE address = ?", 
                  (can_run, address,))
    db.commit()



TEST=False

def sample_target(db, name: str, address: str):
    if TEST:
        result = True
    else:
        result = False

    c = db.cursor()
    q = c.execute("SELECT COUNT(*) FROM targets WHERE address = ?", (address,))
    if q.fetchone()[0] == 0:
        c.execute("INSERT INTO targets (name, address) VALUES (?, ?)",
                  (name, address))

    if result:
        c.execute("UPDATE targets SET responded = TRUE, " +
                  "total_count = total_count + 1, " +
                  "total_success = total_success + 1 " +
                  "WHERE address = ?", (address,))
    else:
        c.execute("UPDATE targets SET responded = FALSE, " +
                  "total_count = total_count + 1 WHERE address = ?", (address,))
    db.commit()


def monitor_targets(db_path_master: str, db_path_local: str, address: str):
    create_db(db_path_local)
    db_master = open_db(db_path_master)
    db_local = open_db(db_path_local)
    set_running(db_master, address, True)

    running = True
    while running:
        targets = []
        c = db_master.cursor()
        q = c.execute("SELECT name, address from targets")
        for entry in q.fetchall():
            targets.append(entry)

        for target in targets:
            time.sleep(1)
            running = can_run(db_master, address)
            target_running = is_running(db_master, target[1])
            if running and target_running:
                sample_target(db_local, target[0], target[1]);
        if TEST:
            set_can_run(db_master, address, False)
        running = can_run(db_master, address)

def init_targets(db_file_path: str, data: list[tuple[str]]):
    create_db(db_file_path)
 
    db = open_db(db_file_path)
    c = db.cursor()
    q = c.execute("DELETE FROM targets")
    db.commit()

    for entry in data:
        target = entry[0]
        address = entry[1]

        c.execute("INSERT INTO targets (name, address) VALUES (?, ?)",
                  (target, address));
    db.commit()
    db.close()


def test():
    data = [("host1", "192.168.33.1"),
            ("host2", "192.168.44.2")]
    db_master = "master.sqlite"
    db_working = "work.sqlite"

    init_targets(db_master, data)
    global TEST
    TEST=True
    set_running(open_db(db_master), data[1][1], True)
    monitor_targets(db_master, db_working, data[0][1])


if __name__ == "__main__":
    # Arguments:
    # test
    # monitor tmp_file_master tmp_file_working src_address
    if len(sys.argv) == 2:
        if sys.argv[1] == 'test':
            test()
            sys.exit(0)
    elif len(sys.argv) == 5:
        if sys.argv[1] == 'monitor':
            monitor_targets(sys.argv[2],
                            sys.argv[3],
                            sys.argv[4])
            sys.exit(0)
    print("usage:")
    print("\tmonitor <master_db> <working_db> <src_address>")
    print("\ttest")
    sys.exit(-1)



