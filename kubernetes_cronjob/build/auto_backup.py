#!/usr/bin/env python3

# Baserow Auto-backup tool to use in Kubernetes Job
# Two envvar are required for execution:
#   CREDS : Contain URL of baserow instance and authentication credentials
#   CONFIG : Contain Retention info and list of Project/Database IDs to auto-backup
# Arguments:
#   -t to actually do backup (without flag will only list number of backups for each database)
#   -d used along -t to run the job without actually changing anything (to check configuration)

import os, sys, logging, time
from datetime import datetime

import yaml, requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("baserow_auto_backup")
DRY_RUN = "-d" in sys.argv
baserow_api_url = ""

def get_access_token(email, username, password):
    """Authenticate against baserow and get an acess token (JWT) don't mind about refresh_token and other props
    """
    try:
        r = requests.post(f"{baserow_api_url}user/token-auth/",
                        data={ "email":email,
                               "username":username,
                               "password":password},
                        timeout=30).json()
        return r["access_token"] if "access_token" in r else "error"
    except Exception as e:
        log.error(f"Auth error : {e}")
        return "error"

def list_snapshots(access_token, dbId, prefix=None):
    """List snapshots for a given database id, return list of {"date":,"name":} of existing snapshots
    """
    result = []
    try:
        r = requests.get(f"{baserow_api_url}snapshots/application/{dbId}/",
                          headers={ "Authorization":f"JWT {access_token}"},
                          timeout=30).json()
        if "error" in r:
            raise Exception(f'Backup list error : {r["error"]}/{r["detail"]}')
        for s in r:
            if prefix and not s["name"].startswith(prefix): continue
            result.append({"id":s["id"], "date":datetime.fromisoformat(s["created_at"][:-1]+'+00:00'), "name":s["name"]})
        return result
    except Exception as e:
        log.error(f"List snapshots error : {e}")
        return "error"

def take_backup(access_token, dbId, name):
    """Create a snapshot of the given database id with the given name
       For ease of use in the GUI, the name should contain the backup date
       the function wait for the backup job to complete before return
    """
    if DRY_RUN:
        log.info(f"DRY: Request to take snapshot of {dbId}")
        return "OK"
    try:
        r = requests.post(f"{baserow_api_url}snapshots/application/{dbId}/",
                          headers={ "Authorization":f"JWT {access_token}"},
                          data={"name":name},
                          timeout=30).json()
        if "error" in r:
            raise Exception(f'Backup error : {r["error"]}/{r["detail"]}')
        for t in range(10):
            time.sleep(5*t)
            s = job_status(access_token, r["id"])
            if s == "error":
                raise Exception(f'Job status error {r["id"]}')
            if s["state"] == "finished" : return r
        log.warning("Backup still running")
        return s
    except Exception as e:
        log.error(f"Create snapshots error : {e}")
        return "error"

def find_snapshot(access_token, snapshotId, name):
    """Find a snapshot id corresponding to given name"""
    res = list_snapshots(access_token, snapshotId)
    if res == "error": return res
    for s in res:
        if s["name"].startswith(name): return s["id"]
    return None

def delete_snapshot(access_token, snapshotId):
    """Delete a snapshot identified by the given snapshotId"""
    if DRY_RUN:
        log.info(f"DRY: Request to delete snapshotId {snapshotId}")
        return "OK"
    try:
        r = requests.delete(f"{baserow_api_url}snapshots/{snapshotId}/",
                            headers={ "Authorization":f"JWT {access_token}"},
                            timeout=30)
        time.sleep(5)
        return r
    except Exception as e:
        log.error(f"Delete snapshots error : {e}")
        return "error"

def find_oldest_snapshot(access_token, dbId, prefix=None):
    """Locate the id of the oldest snapshot"""
    res = list_snapshots(access_token, dbId, prefix)
    if res == "error": return res
    if res:
        oldestDate = res[0]["date"]
        oldestId = res[0]["id"]
        oldestName = res[0]["name"]
        for s in res:
            if s["date"] < oldestDate:
                oldestId = s["id"]
                oldestDate = s["date"]
                oldestName = s["name"]
        return oldestId, oldestDate, oldestName
    return None

def purge_snapshots(access_token, dbId, retention, prefix="Autobackup "):
    """Delete the oldest snapshot if the number of autobackups is above retention"""
    res = list_snapshots(access_token, dbId, prefix)
    if res == "error" : return res
    nb = len(res)
    if nb < 1:
        log.warning(f"Snapshots enumeration error for {id}")
    elif nb > retention:
        res = find_oldest_snapshot(access_token, dbId, prefix)
        if res in ("error", None): return res
        snapshotId, _, snapName = res
        log.info(f"\t-> Purge {snapName}")
        res = delete_snapshot(access_token, snapshotId)
        if res == "error": return res
    return None

def job_status(access_token, jobId):
    try:
        r = requests.get(f"{baserow_api_url}jobs/{jobId}/",
                        headers={ "Authorization":f"JWT {access_token}"},
                        timeout=30).json()
        return r
    except Exception as e:
        log.error(f"Job status error : {e}")
        return "error"


def main():

    global baserow_api_url

    if DRY_RUN:
        log.info("Dry run mode, no change will be done to the system")

    creds = yaml.load(os.getenv("CREDS"), Loader=yaml.Loader)
    baserow_api_url = creds["api_url"]

    setup = yaml.load(os.getenv("CONFIG"), Loader=yaml.Loader)
    retention = setup["retention"]
    log.info(f"Default retention {retention} days")

    for b in setup["backups"]:
        keep = b.get("retention", retention)
        log.info(f'Processing {b["project"]}, retention {keep}')

        token = get_access_token( creds["email"], creds["username"], creds["password"])
        if token == "error":
            log.error("Authentication failure, check credentials")
            return 1

        for i in b["ids"]:
            res = list_snapshots(token, i, prefix="Autobackup ")
            if res == "error":
                log.error("CONFIGURATION ERROR")
                return 1
            log.info(f'\t-> Backup DB {i}, {len(res)} existing Autobackups')
            if "-t" in sys.argv:
                res = take_backup(token, i, f"Autobackup {datetime.utcnow().isoformat()[:19]} UTC")
                if res == "error":
                    log.error("BACKUP FAILURE :")
                    return 1
                res = purge_snapshots(token, i, keep)
                if res == "error":
                    log.error("PURGE ERROR")

    return 0

if __name__ == "__main__":
    sys.exit(main())
