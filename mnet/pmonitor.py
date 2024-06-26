import os
import sys
import sqlite3
import shutil
import time
import subprocess
import mininet.net
import logging


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
    entry = q.fetchone()
    return entry[0]


def set_running(db, address: str, running: bool):
    c = db.cursor()
    q = c.execute(
        "UPDATE targets SET running = ? WHERE address = ?",
        (
            running,
            address,
        ),
    )
    db.commit()


def can_run(db, address: str) -> bool:
    c = db.cursor()
    q = c.execute("SELECT run FROM targets WHERE address = ?", (address,))
    entry = q.fetchone()
    return entry[0]


def set_can_run(db, address: str, can_run):
    c = db.cursor()
    q = c.execute(
        "UPDATE targets SET run = ? WHERE address = ?",
        (
            can_run,
            address,
        ),
    )
    db.commit()


def get_status_count(db, stable: bool):
    c = db.cursor()
    # May sample only stable node connections or all
    if stable:
        q = c.execute("SELECT COUNT(*) FROM targets WHERE stable = TRUE AND responded = TRUE")
        good_targets = q.fetchone()[0]
        q = c.execute("SELECT COUNT(*) FROM targets WHERE stable = TRUE AND total_count > 0")
        total_targets = q.fetchone()[0]
    else:
        q = c.execute("SELECT COUNT(*) FROM targets WHERE responded = TRUE")
        good_targets = q.fetchone()[0]
        q = c.execute("SELECT COUNT(*) FROM targets WHERE total_count > 0")
        total_targets = q.fetchone()[0]
    c.close()
    return good_targets, total_targets

def get_last_five(db) ->list[tuple[str,bool]]:
    c = db.cursor()
    q = c.execute("SELECT name, responded FROM targets ORDER BY sample_time DESC LIMIT 5")
    result = []
    for name, responded in q.fetchall():
        result.append((name, responded))
    return result

def get_status_list(db):
    c = db.cursor()
    q = c.execute("SELECT name, responded FROM targets WHERE total_count > 0")
    result = {}
    for e in q.fetchall():
        result[e[0]] = e[1]
    return result


TEST = False


def sample_target(db, name: str, address: str, stable: bool, src_address: str):
    logging.info("sample target: %s", address)
    process = subprocess.run(
        ["ping", "-I", src_address, "-c1", "-W3", f"{address}"], capture_output=True, text=True
    )
    logging.info("%s", process.stdout)
    sent, received = mininet.net.Mininet._parsePing(process.stdout)
    result = sent == received

    prev_responded = False
    now = time.time()
    c = db.cursor()
    q = c.execute("SELECT responded FROM targets WHERE address = ?", (address,))
    qr = q.fetchall()
    if len(qr) == 0:
        c.execute("INSERT INTO targets (name, address, sample_time, stable) VALUES (?, ?, ?, ?)", (name, address, now, stable))
    else:
        prev_responded = qr[0][0]

    if result:
        c.execute(
            "UPDATE targets SET responded = TRUE, "
            + "sample_time = ?,"
            + "total_count = total_count + 1, "
            + "total_success = total_success + 1 "
            + "WHERE address = ?",
            (
                now,
                address,
            ),
        )
    elif prev_responded:
        c.execute(
            "UPDATE targets SET responded = FALSE, "
            + "sample_time = ?,"
            + "total_count = total_count + 1 WHERE address = ?",
            (
                now,
                address,
            ),
        )
    db.commit()


def monitor_targets(db_path_master: str, db_path_local: str, address: str):
    logging.info("Monitoring targets from %s to %s", address, db_path_local)
    create_db(db_path_local)
    db_master = open_db(db_path_master)
    db_local = open_db(db_path_local)

    # Make an entry for the current monitoring process
    c = db_master.cursor()
    q = c.execute("SELECT name, stable FROM targets WHERE address = ?", (address,))
    name, stable = q.fetchone()
    c.close()
    c = db_local.cursor()
    c.execute("INSERT INTO targets (name, address, stable, me) VALUES (?, ?, ?, TRUE)", (name,address,stable))
    db_local.commit()
    c.close()

    running = True
    while running:
        targets = []
        logging.info("reload target list")
        c = db_master.cursor()
        q = c.execute("SELECT name, address, stable FROM targets")
        for entry in q.fetchall():
            targets.append(entry)

        index = -1
        for i in range(len(targets)):
            if targets[i][1] == address:
                index = i
                break

        if index != -1:
            # Rotate list so all elements are sampling different targets
            tmp = targets[index + 1 :]
            tmp.extend(targets[:index])
            targets = tmp

        for target in targets:
            if not TEST:
                time.sleep(5)
            running = can_run(db_master, address)
            if running:
                sample_target(db_local, target[0], target[1], target[2], address)
        if TEST:
            set_can_run(db_master, address, False)
        running = can_run(db_master, address)


def init_targets(db_file_path: str, data: list[tuple[str,str,bool]]):
    create_db(db_file_path)

    db = open_db(db_file_path)
    c = db.cursor()
    q = c.execute("DELETE FROM targets")
    db.commit()

    for entry in data:
        target = entry[0]
        address = entry[1]
        stable = entry[2]

        c.execute(
            "INSERT INTO targets (name, address, stable) VALUES (?, ?, ?)", (target, address, stable)
        )
    db.commit()
    db.close()


def test():
    data = [
        ("host1", "192.168.33.1", True),
        ("host2", "192.168.44.2", True),
        ("host3", "192.168.55.2", True),
        ("host3", "192.168.55.3", False),
    ]
    db_master = "master.sqlite"
    db_working = "work.sqlite"

    init_targets(db_master, data)
    global TEST
    TEST = True
    set_running(open_db(db_master), data[1][1], True)
    monitor_targets(db_master, db_working, data[0][1])
    monitor_targets(db_master, db_working, data[3][1])
    good, total = get_status_count(open_db(db_working))
    results = get_status_list(open_db(db_working))
    results = get_last_five(open_db(db_working))
    print(f"status {good} / {total}")
    return True


if __name__ == "__main__":
    # Arguments:
    # test
    # monitor tmp_file_master tmp_file_working src_address
    logging.basicConfig(filename=f"/tmp/error_msg.{os.getpid()}", level=logging.INFO)

    if len(sys.argv) == 2:
        if sys.argv[1] == "test":
            logging.info("Starting test")
            test()
            sys.exit(0)
    elif len(sys.argv) == 5:
        if sys.argv[1] == "monitor":
            try:
                monitor_targets(sys.argv[2], sys.argv[3], sys.argv[4])
                sys.exit(0)
            except Exception as e:
                logging.error(str(e))
                sys.exit(-1)
    print("usage:")
    print("\tmonitor <master_db> <working_db> <src_address>")
    print("\ttest")
    sys.exit(-1)
