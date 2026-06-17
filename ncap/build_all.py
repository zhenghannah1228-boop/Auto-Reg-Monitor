"""按顺序跑全部测试项 build,重建 ncap_matrix.json。"""
import subprocess, sys, os
os.environ["PYTHONPATH"] = "/tmp/pylibs:" + os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["build_frontal_rigid_full.py", "build_frontal_mpdb_offset.py", "build_frontal_small_overlap.py",
           "build_side_impact.py", "build_side_pole.py", "build_whiplash_rear.py", "build_vru_passive.py",
           "build_ev_hazard.py", "build_post_crash_safety.py", "build_restraint_system.py",
           "build_adas_aeb.py", "build_vru_active.py", "build_lane_support.py", "build_blind_spot.py",
           "build_adaptive_highbeam.py", "build_occupant_monitoring.py"]
fail = 0
for s in SCRIPTS:
    print(f"\n===== {s} =====")
    r = subprocess.run([sys.executable, s], env=os.environ)
    fail += (r.returncode != 0)
print(f"\n>>> 全部 {len(SCRIPTS)} 个 build 完成,失败 {fail}")
sys.exit(1 if fail else 0)
