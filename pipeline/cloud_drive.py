"""Start / poll the server-side render driver of a DEPLOYED project app (deploy first: VL_PROJECT=<p> python3 -m modal deploy modal_render.py).
  python3 cloud_drive.py start <project> '{"chunk":24,"resume":true,"force":["s01"],"tag":"pass2"}'
  python3 cloud_drive.py start <project> '{"segments":24,"tag":"comp"}' drive_composite
  python3 cloud_drive.py status <call_id>"""
import modal, sys, json
cmd = sys.argv[1]
if cmd == "start":
    proj, kw = sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    fn = sys.argv[4] if len(sys.argv) > 4 else "drive"   # drive | drive_composite
    fc = modal.Function.from_name(f"vl-render-{proj}", fn).spawn(**kw); print(fc.object_id)
elif cmd == "status":
    fc = modal.FunctionCall.from_id(sys.argv[2])
    try: print("DONE", fc.get(timeout=0))
    except TimeoutError: print("RUNNING")
