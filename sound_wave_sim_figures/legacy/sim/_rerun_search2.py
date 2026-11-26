import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize

def main():
    study = optimize.search(workers=8)
    optimize.save(study["rows"], {"best_pair": study["best_pair"],
                                  "best_three": study["best_three"]},
                  Path("../data"))
    print("best pair", study["best_pair"]["short"], study["best_pair"]["band_max_db"],
          study["best_pair"]["bw6_xz_deg"])
    print("best three", study["best_three"]["short"], study["best_three"]["offsets"],
          study["best_three"]["band_max_db"], study["best_three"]["bw6_xz_deg"])

if __name__ == "__main__":
    main()
