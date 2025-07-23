import pandas as pd
from pathlib import Path
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from data_handler import load_data, convert_file, search_dataframe

def test_load_data_with_params(tmp_path):
    p = tmp_path / "sample.csv"
    p.write_text("a;b\n1;2", encoding="utf-8")
    df = load_data(str(p), None, "utf-8", ";")
    assert df.shape == (1, 2)


def test_convert_file(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    src = tmp_path / "data.csv"
    df.to_csv(src, index=False)
    out = convert_file(str(src), str(tmp_path), "xlsx")
    assert Path(out).exists()


def test_search_dataframe():
    df = pd.DataFrame({"col": ["Foo", "bar", "foo"]})
    idx = search_dataframe(df, "foo", column="col", case=False)
    assert idx == [0, 2]
    idx_case = search_dataframe(df, "foo", column="col", case=True)
    assert idx_case == [2]
