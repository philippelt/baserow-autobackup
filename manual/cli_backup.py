#!/usr/bin/env python3

# Baserow Auto-backup tool to use interactively or cron script shells
# envvar required for execution:
#   BASEROW_USER : Your login baserow username
#   BASEROW_PWD : Your login password
#   BASEROW_EMAIL : Your email
#   BASEROW_API_URL : The URL to reach api on your baserow instance eg: https://baserow.example.com/api/

# Usage:
# ./cli_backup.py <Database/Application ID> <Action> [<action parameter>]
#       where action is one of : list, listAuto, oldest, oldestAuto, take, delete, job, purge
#       list will list all backups, listAuto only those which name startswith Autobackup
#       oldest will find oldest of all backups, oldestAuto only in Autobackups
#       purge will keep only the n last auto-backups
# Action parameters for :
#       take [<name for the created backup>]
#     delete <name of the backup to delete>
#        job <jobId> of the job for which info is requested
#      purge [<number of backups to keep>] if not provided, 10 by default


import os, sys, logging, time
from datetime import datetime
from pprint import pprint

import requests

log = logging.getLogger("baserow_auto_backup")
BASEROW_API_URL = os.getenv('BASEROW_API_URL')
BASEROW_USER = os.getenv('BASEROW_USER')
BASEROW_EMAIL = os.getenv('BASEROW_EMAIL')
BASEROW_PWD = os.getenv('BASEROW_PWD')

def get_access_token():
    """Authenticate against baserow and get an acess token (JWT) don't mind about refresh_token and other props
    """
    try:
        r = requests.post(f"{BASEROW_API_URL}user/token-auth/",
                        data={ "email":BASEROW_EMAIL,
                               "username":BASEROW_USER,
                               "password":BASEROW_PWD},
                        timeout=30).json()
        if "access_token" in r:
            return r["access_token"]
        return "error"
    except Exception as e:
        log.error(f"Auth error : {e}")
        return "error"

def list_snapshots(access_token, dbId, prefix=None):
    """List snapshots for a given database id, return list of {"date":,"name":} of existing snapshots
    """
    result = []
    try:
        r = requests.get(f"{BASEROW_API_URL}snapshots/application/{dbId}/",
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
    """
    try:
        r = requests.post(f"{BASEROW_API_URL}snapshots/application/{dbId}/",
                          headers={ "Authorization":f"JWT {access_token}"},
                          data={"name":name},
                          timeout=30).json()
        if "error" in r:
            raise Exception(f'Backup error : {r["error"]}/{r["detail"]}')
        for t in range(10):
            time.sleep(4*t)
            s = job_status(access_token, r["id"])
            if s == "error":
                raise Exception(f'Job status error {r["id"]}')
            if s["state"] == "finished" : return s
        raise Exception("Backup still running")
    except Exception as e:
        log.error(f"Create snapshots error : {e}")
        return "error"

def find_snapshot(access_token, dbId, name):
    """Find a snapshot id corresponding to given name"""
    res = list_snapshots(access_token, dbId)
    if res == "error": return res
    for s in res:
        if s["name"].startswith(name): return s["id"]
    return None

def delete_snapshot(access_token, snapshotId):
    """Delete a snapshot identified by the giver snapshotId"""
    try:
        r = requests.delete(f"{BASEROW_API_URL}snapshots/{snapshotId}/",
                            headers={ "Authorization":f"JWT {access_token}"},
                            timeout=30)
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

def job_status(access_token, jobId):
    try:
        r = requests.get(f"{BASEROW_API_URL}jobs/{jobId}/",
                        headers={ "Authorization":f"JWT {access_token}"},
                        timeout=30).json()
        return r
    except Exception as e:
        log.error(f"Job status error : {e}")
        return "error"


def usage():
    print("Usage   ./cli_backup.py <Database/Application ID> <Action> [<action parameter>]")
    print("\twhere action is one of : list, listAuto, oldest, oldestAuto, take, delete, job, purge")
    print("Action parameters for :")
    print("\ttake: name for the created backup")
    print("\tdelete: name of the backup to delete")
    print("\tjob: job id to get status")
    print("\tpurge: number of auto-backups to keep (default 10)")


def main():

    if not (BASEROW_EMAIL and BASEROW_PWD and BASEROW_USER and BASEROW_API_URL):
        log.error("Credentials and/or URL envvar missing BASEROW_xxx")
        return 1

    if len(sys.argv) < 3:
        log.error("Arguments missing")
        usage()
        return 1

    print("Database :", (dbId := sys.argv[1]))
    print("Action :", (action := sys.argv[2].lower()))

    if action not in ("list", "listAuto", "oldest", "oldestAuto", "take", "delete", "job", "purge"):
        log.error(f"Unrecognized action {action}")
        usage()
        return 1

    if (access_token := get_access_token()) == "error": return 1

    match action:

        case 'list':
            res = list_snapshots(access_token, dbId)
            if res == "error": return 1
            print(f"{len(res)} Snapshots available")
            pprint(res)

        case 'listAuto':
            res = list_snapshots(access_token, dbId, prefix="Autobackup ")
            if res == "error": return 1
            print(f"{len(res)} Snapshots available")
            pprint(res)

        case 'oldest':
            res = find_oldest_snapshot(access_token, dbId)
            if res == "error": return 1
            pprint(res)

        case 'oldestAuto':
            res = find_oldest_snapshot(access_token, dbId, prefix="Autobackup ")
            if res == "error": return 1
            pprint(res)

        case 'take':
            name = sys.argv[3] if len(sys.argv) > 3 else f"Autobackup {datetime.utcnow().isoformat()[:19]} UTC"
            res = take_backup(access_token, dbId, name)
            if res == "error": return 1
            pprint(res)

        case 'delete':
            if len(sys.argv) < 4 :
                print("Missing backup name")
                usage()
                return 1
            name = sys.argv[3]
            snapshotId = find_snapshot(access_token, dbId, name)
            if snapshotId == "error": return 1
            if snapshotId is None:
                print("Backup not found")
                return 1
            print(f"Deleting snapshot {name} ({snapshotId})")
            res = delete_snapshot(access_token, snapshotId)
            if res == "error": return 1
            pprint(res)

        case "job":
            if len(sys.argv) < 4 :
                print("Missing job Id")
                return 1
            jobId = sys.argv[3]
            pprint(job_status(access_token, jobId))

        case "purge":
            keep = int(sys.argv[3]) if len(sys.argv) == 4 else 10
            print(f"Purge keeping {keep} auto backups")
            res = list_snapshots(access_token, dbId, prefix="Autobackup ")
            toDelete = len(res) - keep
            if toDelete > 0:
                for _ in range(toDelete):
                    snapshotId, _, name = find_oldest_snapshot(access_token, dbId, prefix="Autobackup ")
                    print(f"Deleting snapshot {name} ({snapshotId})")
                    res = delete_snapshot(access_token, snapshotId)
                    if res == "error": return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
