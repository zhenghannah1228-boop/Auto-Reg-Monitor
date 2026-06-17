"""按顺序逐个跑全部测试项 build,重建 ncap_matrix.json(稳优先)。
- 串行:每个 build 独立子进程,跑完即退出释放全部内存,再起下一个;
- 内存兜底:子进程设 RLIMIT_AS 软上限(默认 2GB),失控时子进程自身干净失败,
  不触发系统 OOM killer 误杀父进程或其他进程;
- 单个 build 失败不中断整批,末尾汇总失败清单。
L3 阈值拆进来后数据翻倍,逐页 flush_cache(见 extract_common._flush)+ 串行 + 上限三重保险。"""
import subprocess, sys, os, resource

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["PYTHONPATH"] = "/tmp/pylibs:" + HERE
MEM_CAP_GB = float(os.environ.get("NCAP_MEM_CAP_GB", "2"))

SCRIPTS = ["build_frontal_rigid_full.py", "build_frontal_mpdb_offset.py", "build_frontal_small_overlap.py",
           "build_side_impact.py", "build_side_pole.py", "build_whiplash_rear.py", "build_vru_passive.py",
           "build_ev_hazard.py", "build_post_crash_safety.py", "build_restraint_system.py",
           "build_adas_aeb.py", "build_vru_active.py", "build_lane_support.py", "build_blind_spot.py",
           "build_adaptive_highbeam.py", "build_occupant_monitoring.py"]


def _limit_mem():
    """子进程入口前设虚拟内存软上限,超限触发 MemoryError 而非系统 OOM。"""
    cap = int(MEM_CAP_GB * 1024 ** 3)
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        new_hard = hard if hard != resource.RLIM_INFINITY and hard < cap else cap
        resource.setrlimit(resource.RLIMIT_AS, (cap, new_hard))
    except (ValueError, OSError):
        pass


def main():
    failed = []
    for s in SCRIPTS:
        print(f"\n===== {s} =====", flush=True)
        r = subprocess.run([sys.executable, s], cwd=HERE, env=os.environ, preexec_fn=_limit_mem)
        if r.returncode != 0:
            failed.append((s, r.returncode))
            print(f"  ✗ {s} 退出码 {r.returncode}(已跳过,继续下一个)", flush=True)
    print(f"\n>>> 全部 {len(SCRIPTS)} 个 build 完成;失败 {len(failed)}"
          + (" — " + ", ".join(f"{n}({c})" for n, c in failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
