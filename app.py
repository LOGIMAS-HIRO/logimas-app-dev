import json
import re
from io import BytesIO
from pathlib import Path
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CSV/Excel マッピングツール", layout="wide")

TEMPLATE_DIR = Path("templates")
TEMPLATE_DIR.mkdir(exist_ok=True)
RULES_FILE = Path("rules.json")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme123")

BASIC_FIELDS = [
    "受注番号", "送り状種別", "温度帯", "出荷日", "指定日", "指定時間",
    "届け先郵便番号", "届け先電話番号", "届け先名", "届け先住所1", "届け先住所2",
    "ご依頼主郵便番号", "ご依頼主電話番号", "ご依頼主名", "ご依頼主住所1", "ご依頼主住所2",
    "商品コード1", "商品名1", "数量", "記事",
]

COMMON_FIELDS = [
    "受注番号", "送り状種別", "温度帯", "出荷日", "指定日", "指定時間", "届け先コード",
    "届け先電話番号", "届け先電話番号枝番", "届け先郵便番号", "届け先住所1", "届け先住所2",
    "届け先会社・部門1", "届け先会社・部門2", "届け先名", "届け先名カナ", "敬称",
    "ご依頼主コード", "ご依頼主電話番号", "ご依頼主電話番号枝番", "ご依頼主郵便番号",
    "ご依頼主住所1", "ご依頼主住所2", "ご依頼主名", "ご依頼主名カナ",
    "商品コード1", "商品名1", "商品コード2", "商品名2", "数量", "荷扱い1", "荷扱い2", "記事",
    "コレクト代金引換額", "内消費税額等", "止置き", "営業所コード", "発行枚数", "個数口表示フラグ",
    "請求先顧客コード", "請求先分類コード", "運賃管理番号", "クロネコwebコレクトデータ登録",
    "クロネコwebコレクト加盟店番号", "クロネコwebコレクト申込受付番号1", "クロネコwebコレクト申込受付番号2",
    "クロネコwebコレクト申込受付番号3", "お届け予定eメール利用区分", "お届け予定eメールアドレス", "入力機種",
    "お届け予定eメールメッセージ", "お届け完了eメール利用区分", "お届け完了eメールアドレス",
    "お届け完了eメールメッセージ", "クロネコ収納代行利用区分", "予備1", "収納代行請求金額税込",
    "収納代行内消費税額等", "収納代行請求先郵便番号", "収納代行請求先住所", "収納代行請求先住所マンション",
    "収納代行請求先会社部門名1", "収納代行請求先会社部門名2", "収納代行請求先名漢字", "収納代行請求先名カナ",
    "収納代行問合せ先名漢字", "収納代行問合せ先郵便番号", "収納代行問合せ先住所", "収納代行問合せ先住所マンション",
    "収納代行問合せ先電話番号", "収納代行管理番号", "収納代行品名", "収納代行備考", "複数口くくりキー",
    "検索キータイトル1", "検索キー1", "検索キータイトル2", "検索キー2", "検索キータイトル3", "検索キー3",
    "検索キータイトル4", "検索キー4", "検索キータイトル5", "検索キー5", "予備2", "予備3",
    "投函予定メール利用区分", "投函予定メールアドレス", "投函予定メールメッセージ",
    "投函完了メールお届け先利用区分", "投函完了メールお届け先アドレス", "投函完了メールお届け先メッセージ",
    "投函完了メールご依頼主利用区分", "投函完了メールご依頼主アドレス", "投函完了メールご依頼主メッセージ",
]

YAMATO_FIELDS = [
    "お客様管理番号", "送り状種類", "クール区分", "伝票番号", "出荷予定日", "お届け予定日", "配達時間帯",
    "お届け先コード", "お届け先電話番号", "お届け先電話番号枝番", "お届け先郵便番号", "お届け先住所",
    "お届け先アパートマンション名", "お届け先会社・部門１", "お届け先会社・部門２", "お届け先名",
    "お届け先名(ｶﾅ)", "敬称", "ご依頼主コード", "ご依頼主電話番号", "ご依頼主電話番号枝番",
    "ご依頼主郵便番号", "ご依頼主住所", "ご依頼主アパートマンション", "ご依頼主名", "ご依頼主名(ｶﾅ)",
    "品名コード１", "品名１", "品名コード２", "品名２", "荷扱い１", "荷扱い２", "記事", "ｺﾚｸﾄ代金引換額（税込)",
    "内消費税額等", "止置き", "営業所コード", "発行枚数", "個数口表示フラグ", "請求先顧客コード", "請求先分類コード",
    "運賃管理番号", "クロネコwebコレクトデータ登録", "クロネコwebコレクト加盟店番号", "クロネコwebコレクト申込受付番号１",
    "クロネコwebコレクト申込受付番号２", "クロネコwebコレクト申込受付番号３", "お届け予定ｅメール利用区分",
    "お届け予定ｅメールe-mailアドレス", "入力機種", "お届け予定ｅメールメッセージ", "お届け完了ｅメール利用区分",
    "お届け完了ｅメールe-mailアドレス", "お届け完了ｅメールメッセージ", "クロネコ収納代行利用区分", "予備",
    "収納代行請求金額(税込)", "収納代行内消費税額等", "収納代行請求先郵便番号", "収納代行請求先住所",
    "収納代行請求先住所（アパートマンション名）", "収納代行請求先会社・部門名１", "収納代行請求先会社・部門名２",
    "収納代行請求先名(漢字)", "収納代行請求先名(カナ)", "収納代行問合せ先名(漢字)", "収納代行問合せ先郵便番号",
    "収納代行問合せ先住所", "収納代行問合せ先住所（アパートマンション名）", "収納代行問合せ先電話番号", "収納代行管理番号",
    "収納代行品名", "収納代行備考", "複数口くくりキー", "検索キータイトル1", "検索キー1", "検索キータイトル2", "検索キー2",
    "検索キータイトル3", "検索キー3", "検索キータイトル4", "検索キー4", "検索キータイトル5", "検索キー5", "予備2", "予備3",
    "投函予定メール利用区分", "投函予定メールe-mailアドレス", "投函予定メールメッセージ",
    "投函完了メール（お届け先宛）利用区分", "投函完了メール（お届け先宛）e-mailアドレス",
    "投函完了メール（お届け先宛）メールメッセージ", "投函完了メール（ご依頼主宛）利用区分",
    "投函完了メール（ご依頼主宛）e-mailアドレス", "投函完了メール（ご依頼主宛）メールメッセージ",
]

# --- template/config helpers ---
def list_templates():
    return sorted([p.stem for p in TEMPLATE_DIR.glob("*.json")])

def load_template(template_name):
    path = TEMPLATE_DIR / f"{template_name}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_template(template_name, data):
    path = TEMPLATE_DIR / f"{template_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def delete_template(template_name):
    path = TEMPLATE_DIR / f"{template_name}.json"
    if path.exists():
        path.unlink()

def default_config():
    return {
        "mode": "通常モード",
        "show_detail": False,
        "show_transform_detail": True,
        "mapping": {field: "（未選択）" for field in COMMON_FIELDS},
        "fixed_values": {field: "" for field in COMMON_FIELDS},
        "rule_selection": {field: "（なし）" for field in COMMON_FIELDS},
        "rename_fields": {field: field for field in COMMON_FIELDS},
        "output_flags": {field: (field in BASIC_FIELDS) for field in COMMON_FIELDS},
        "ordered_output_fields": BASIC_FIELDS.copy(),
    }

def init_session():
    defaults = {
        "template_active_name": "（新規）",
        "template_pending_name": None,
        "template_save_message": "",
        "template_delete_message": "",
        "config_loaded": False,
        "widget_gen": 0,
        "last_rule_target": None,
        "rule_editor_rows": [{"変換前": "", "変換後": ""}],
        "template_selector_widget": "（新規）",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not st.session_state["config_loaded"]:
        apply_config(default_config())
        st.session_state["config_loaded"] = True

def apply_config(config):
    st.session_state["mode_model"] = config.get("mode", "通常モード")
    st.session_state["show_detail_model"] = config.get("show_detail", False)
    st.session_state["show_transform_detail_model"] = config.get("show_transform_detail", True)
    st.session_state["mapping_model"] = config.get("mapping", {field: "（未選択）" for field in COMMON_FIELDS})
    st.session_state["fixed_values_model"] = config.get("fixed_values", {field: "" for field in COMMON_FIELDS})
    st.session_state["rule_selection_model"] = config.get("rule_selection", {field: "（なし）" for field in COMMON_FIELDS})
    st.session_state["rename_fields_model"] = config.get("rename_fields", {field: field for field in COMMON_FIELDS})
    output_flags = config.get("output_flags", {field: (field in BASIC_FIELDS) for field in COMMON_FIELDS})
    st.session_state["output_flags_model"] = {field: bool(output_flags.get(field, False)) for field in COMMON_FIELDS}
    ordered = [f for f in config.get("ordered_output_fields", BASIC_FIELDS.copy()) if f in COMMON_FIELDS and output_flags.get(f, False)]
    for field in COMMON_FIELDS:
        if st.session_state["output_flags_model"].get(field, False) and field not in ordered:
            ordered.append(field)
    st.session_state["ordered_output_fields_model"] = ordered
    st.session_state["widget_gen"] += 1

def collect_config_from_models():
    output_flags = st.session_state["output_flags_model"].copy()
    ordered = [f for f in st.session_state["ordered_output_fields_model"] if output_flags.get(f, False)]
    for field in COMMON_FIELDS:
        if output_flags.get(field, False) and field not in ordered:
            ordered.append(field)
    return {
        "mode": st.session_state["mode_model"],
        "show_detail": st.session_state["show_detail_model"],
        "show_transform_detail": st.session_state["show_transform_detail_model"],
        "mapping": st.session_state["mapping_model"].copy(),
        "fixed_values": st.session_state["fixed_values_model"].copy(),
        "rule_selection": st.session_state["rule_selection_model"].copy(),
        "rename_fields": st.session_state["rename_fields_model"].copy(),
        "output_flags": output_flags,
        "output_fields": [f for f in COMMON_FIELDS if output_flags.get(f, False)],
        "ordered_output_fields": ordered,
    }



def inject_custom_style():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1120;
            --bg2: #111827;
            --line: rgba(148, 163, 184, 0.18);
            --text: #f8fafc;
            --muted: #cbd5e1;
            --brand: #4f76a1;
            --brand2: #355a86;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(79,118,161,0.18) 0%, rgba(79,118,161,0) 24%),
                radial-gradient(circle at top right, rgba(53,90,134,0.14) 0%, rgba(53,90,134,0) 22%),
                linear-gradient(180deg, #10192b 0%, #172235 100%);
            color: var(--text);
        }

        .block-container { padding-top: 1rem; padding-bottom: 2rem; }

        h1, h2, h3, h4, h5, h6, p, div, label, span,
        .stMarkdown, .stCaption, [data-testid="stMarkdownContainer"] * {
            color: var(--text) !important;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-right: 1px solid var(--line);
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(15, 23, 42, 0.96) !important;
            color: var(--text) !important;
            border: 1px solid var(--line) !important;
            border-radius: 18px !important;
        }

        input, textarea, div[data-baseweb="select"] *, div[data-baseweb="input"] * {
            color: var(--text) !important;
        }

        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            border-radius: 999px !important;
            border: 1px solid rgba(148,163,184,0.22) !important;
            background: linear-gradient(135deg, var(--brand) 0%, var(--brand2) 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            padding: 0.58rem 1.14rem !important;
        }

        [data-testid="stCheckbox"] label,
        [data-testid="stCheckbox"] p,
        [data-testid="stRadio"] label,
        [data-testid="stFileUploaderDropzone"] * {
            color: var(--text) !important;
        }

        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"],
        [data-testid="stDataFrame"] > div,
        [data-testid="stDataEditor"] > div,
        [data-testid="stDataFrameGlideDataEditor"],
        [data-testid="stDataEditor"] [data-testid="stDataFrameGlideDataEditor"] {
            background: #0b1220 !important;
            color: #ffffff !important;
            border: 1px solid rgba(148,163,184,0.20) !important;
            border-radius: 20px !important;
            overflow: hidden !important;
            --gdg-bg-cell: #0b1220;
            --gdg-bg-cell-medium: #111827;
            --gdg-bg-header: #172033;
            --gdg-bg-header-has-focus: #22304a;
            --gdg-bg-header-hovered: #22304a;
            --gdg-text-dark: #ffffff;
            --gdg-text-medium: #f1f5f9;
            --gdg-text-light: #cbd5e1;
            --gdg-border-color: rgba(148,163,184,0.18);
            --gdg-horizontal-border-color: rgba(148,163,184,0.16);
            --gdg-vertical-border-color: rgba(148,163,184,0.12);
            --gdg-accent-color: #4f76a1;
            --gdg-accent-fg: #ffffff;
            --gdg-bg-icon-header: #e2e8f0;
        }

        [data-testid="stDataFrame"] *,
        [data-testid="stDataEditor"] *,
        [data-testid="stDataFrameGlideDataEditor"] *,
        [data-testid="stDataEditor"] [data-testid="stDataFrameGlideDataEditor"] * {
            color: #ffffff !important;
        }

        [data-testid="stDataFrame"] canvas,
        [data-testid="stDataEditor"] canvas { background: #0b1220 !important; }

        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataEditor"] [role="columnheader"],
        [data-testid="stDataFrame"] [class*="header"],
        [data-testid="stDataEditor"] [class*="header"] {
            background: #172033 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }

        [data-testid="stDataFrame"] [role="gridcell"],
        [data-testid="stDataEditor"] [role="gridcell"],
        [data-testid="stDataFrame"] [role="rowheader"],
        [data-testid="stDataEditor"] [role="rowheader"],
        [data-testid="stDataFrame"] [class*="gdg"],
        [data-testid="stDataEditor"] [class*="gdg"] {
            background: #0b1220 !important;
            color: #ffffff !important;
            border-color: rgba(148,163,184,0.18) !important;
        }

        [data-testid="stDataEditor"] input,
        [data-testid="stDataEditor"] textarea,
        [data-testid="stDataFrame"] input,
        [data-testid="stDataFrame"] textarea {
            background: #0f172a !important;
            color: #ffffff !important;
            caret-color: #ffffff !important;
            border: 1px solid rgba(148,163,184,0.22) !important;
        }

        [data-testid="stDataFrame"] svg,
        [data-testid="stDataEditor"] svg,
        [data-testid="stDataFrame"] path,
        [data-testid="stDataEditor"] path {
            color: #e2e8f0 !important;
            fill: #e2e8f0 !important;
        }

        [data-testid="stDataFrame"] [aria-selected="true"],
        [data-testid="stDataEditor"] [aria-selected="true"] {
            background: #1d4ed8 !important;
            color: #ffffff !important;
        }

        [data-testid="stDataFrame"] div[role="gridcell"] *,
        [data-testid="stDataEditor"] div[role="gridcell"] *,
        [data-testid="stDataFrame"] div[role="columnheader"] *,
        [data-testid="stDataEditor"] div[role="columnheader"] *,
        [data-testid="stDataFrame"] [data-testid*="RowHeader"],
        [data-testid="stDataEditor"] [data-testid*="RowHeader"] {
            color: #ffffff !important;
        }

        [data-testid="stAlert"] {
            border-radius: 16px !important;
            border: 1px solid var(--line) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("## ログイン")
    st.caption("CSV/Excel 変換システムへアクセスするにはパスワードを入力してください。")

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")

    if submitted:
        if pw == APP_PASSWORD:
            st.session_state["authenticated"] = True
            show_login_processing()
            return False
        else:
            st.error("パスワードが違います。")
    return False


def show_login_processing():
    placeholder = st.empty()
    placeholder.markdown(
        """
        <div style="
            margin: 20px 0 10px 0;
            padding: 16px 18px;
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.18);
            color: #f8fafc;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        ">
            ログイン中…
        </div>
        """,
        unsafe_allow_html=True,
    )

class TemplateManager:
    NEW_LABEL = "（新規）"
    SELECTBOX_KEY = "template_selector_widget"

    def render_selector_and_sync(self):
        options = [self.NEW_LABEL] + list_templates()

        pending = st.session_state.get("template_pending_name")
        if pending is not None:
            # selectbox描画前にだけ値を差し替える
            st.session_state[self.SELECTBOX_KEY] = pending if pending in options else self.NEW_LABEL
        elif st.session_state.get(self.SELECTBOX_KEY) not in options:
            st.session_state[self.SELECTBOX_KEY] = self.NEW_LABEL

        selected = st.selectbox("テンプレート選択", options, key=self.SELECTBOX_KEY)

        # まだ予約がない状態で選択が変わったら、まず次回反映予約だけして再描画
        if pending is None and selected != st.session_state["template_active_name"]:
            st.session_state["template_pending_name"] = selected
            st.rerun()

        # 予約されたテンプレートを今回適用
        pending_apply = st.session_state.get("template_pending_name")
        if pending_apply is not None:
            if pending_apply == self.NEW_LABEL:
                apply_config(default_config())
                st.session_state["template_active_name"] = self.NEW_LABEL
            else:
                data = load_template(pending_apply)
                if data is not None:
                    apply_config(data)
                    st.session_state["template_active_name"] = pending_apply
                else:
                    apply_config(default_config())
                    st.session_state["template_active_name"] = self.NEW_LABEL
                    pending_apply = self.NEW_LABEL

            st.session_state["template_pending_name"] = None
            st.rerun()

        return st.session_state["template_active_name"]

    def save_current_as(self, name):
        save_template(name, collect_config_from_models())
        st.session_state["template_save_message"] = f"テンプレート『{name}』を保存しました"
        st.session_state["template_pending_name"] = name
        st.session_state["template_active_name"] = name
        st.rerun()

    def delete_active(self, selected_name):
        delete_template(selected_name)
        st.session_state["template_delete_message"] = f"テンプレート『{selected_name}』を削除しました"
        st.session_state["template_pending_name"] = self.NEW_LABEL
        st.session_state["template_active_name"] = self.NEW_LABEL
        st.rerun()

# --- other helpers ---
def load_rules():
    if not RULES_FILE.exists():
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}

def save_rules(data):
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_series(series):
    return series.astype(str).str.strip().replace("nan", "")

def format_date(value):
    if value == "":
        return ""
    try:
        value_str = str(value).strip()
        if value_str == "":
            return ""
        if "/" in value_str:
            dt = pd.to_datetime(value_str)
            return dt.strftime("%Y/%m/%d")
        value_str = str(int(float(value_str)))
        dt = pd.to_datetime(value_str, format="%Y%m%d")
        return dt.strftime("%Y/%m/%d")
    except Exception:
        return value

def apply_rule(series, rule_dict):
    if not rule_dict:
        return series
    cleaned = clean_series(series)
    return cleaned.map(rule_dict).fillna(cleaned)

def normalize_rule_rows(df_rule):
    if df_rule is None or len(df_rule) == 0:
        return [{"変換前": "", "変換後": ""}]
    rows = []
    for _, row in df_rule.iterrows():
        before = "" if pd.isna(row.get("変換前", "")) else str(row.get("変換前", "")).strip()
        after = "" if pd.isna(row.get("変換後", "")) else str(row.get("変換後", "")).strip()
        if before != "" or after != "":
            rows.append({"変換前": before, "変換後": after})
    return rows if rows else [{"変換前": "", "変換後": ""}]

def rule_rows_to_dict(rule_rows):
    rule_dict = {}
    for row in rule_rows:
        before = str(row.get("変換前", "")).strip()
        after = str(row.get("変換後", "")).strip()
        if before != "":
            rule_dict[before] = after
    return rule_dict

def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="output")
    output.seek(0)
    return output.getvalue()

def move_item_up(items, target):
    idx = items.index(target)
    if idx > 0:
        items[idx - 1], items[idx] = items[idx], items[idx - 1]
    return items

def move_item_down(items, target):
    idx = items.index(target)
    if idx < len(items) - 1:
        items[idx + 1], items[idx] = items[idx], items[idx + 1]
    return items

def build_field_transform_preview(field, source_series, result_series, rule_dict=None):
    src = clean_series(source_series)
    dst = clean_series(result_series)
    compare_df = pd.DataFrame({"元": src, "変換後": dst})
    changed_mask = (compare_df["元"] != compare_df["変換後"]) & (compare_df["元"] != "")
    changed_count = int(changed_mask.sum())
    unique_source_nonblank = sorted([v for v in src.dropna().unique().tolist() if str(v).strip() != ""])
    unconverted_mask = (compare_df["元"] == compare_df["変換後"]) & (compare_df["元"] != "")
    unconverted_values = sorted(compare_df.loc[unconverted_mask, "元"].dropna().unique().tolist())
    leak_candidates = []
    if rule_dict:
        rule_keys = {str(k).strip() for k in rule_dict.keys()}
        leak_candidates = [v for v in unique_source_nonblank if v not in rule_keys]
    changed_pairs_df = (
        compare_df.loc[changed_mask].value_counts().reset_index(name="件数").rename(columns={"元": "元の値", "変換後": "変換後の値"})
    )
    unconverted_df = pd.DataFrame({"未変換値": unconverted_values}) if unconverted_values else pd.DataFrame(columns=["未変換値"])
    leak_df = pd.DataFrame({"ルール漏れ候補": leak_candidates}) if leak_candidates else pd.DataFrame(columns=["ルール漏れ候補"])
    return {"field": field, "changed_count": changed_count, "source_unique_count": len(unique_source_nonblank), "unconverted_count": len(unconverted_values), "leak_count": len(leak_candidates), "changed_pairs_df": changed_pairs_df, "unconverted_df": unconverted_df, "leak_df": leak_df}

def build_all_transform_previews(df, common_df, mapping, fixed_values, rule_selection, rules_master):
    previews = []
    for field in COMMON_FIELDS:
        selected_col = mapping.get(field, "（未選択）")
        fixed_val = str(fixed_values.get(field, "")).strip()
        rule_name = rule_selection.get(field, "（なし）")
        rule_dict = rules_master.get(rule_name, {}) if rule_name != "（なし）" else {}
        if selected_col in ["（未選択）", "（空白）"] and fixed_val == "" and rule_name == "（なし）":
            continue
        source_series = df[selected_col] if selected_col in df.columns else pd.Series([""] * len(common_df), index=common_df.index)
        result_series = common_df[field] if field in common_df.columns else pd.Series([""] * len(common_df), index=common_df.index)
        preview = build_field_transform_preview(field, source_series, result_series, rule_dict)
        preview["selected_col"] = selected_col
        preview["fixed_value"] = fixed_val
        preview["rule_name"] = rule_name
        previews.append(preview)
    return previews

def validate_yamato_required(output_df):
    required_cols = ["お客様管理番号", "送り状種類", "出荷予定日", "お届け先電話番号", "お届け先郵便番号", "お届け先住所", "お届け先名", "ご依頼主電話番号", "ご依頼主郵便番号", "ご依頼主住所", "ご依頼主名", "品名１"]
    missing_cols = []
    for col in required_cols:
        if col not in output_df.columns:
            missing_cols.append(col)
        else:
            col_series = output_df[col].astype(str).str.strip().replace("nan", "")
            if (col_series == "").any():
                missing_cols.append(col)
    return missing_cols

def validate_yamato_format(output_df):
    errors = []
    warnings = []
    def normalized(col):
        if col not in output_df.columns:
            return pd.Series([""] * len(output_df), index=output_df.index)
        return output_df[col].astype(str).str.strip().replace("nan", "")
    def check_regex(col, pattern, message, allow_blank=False, level="error"):
        series = normalized(col)
        invalid = []
        for i, val in series.items():
            if val == "":
                if allow_blank:
                    continue
                invalid.append(i + 1)
            elif not re.fullmatch(pattern, val):
                invalid.append(i + 1)
        if invalid:
            text = f"{col}: {message}（行: {', '.join(map(str, invalid[:10]))}）"
            if len(invalid) > 10:
                text += " ほか"
            if level == "error":
                errors.append(text)
            else:
                warnings.append(text)
    check_regex("送り状種類", r"[0-9A-Z]", "1文字のヤマト送り状種類コードで入力してください", False, "error")
    check_regex("クール区分", r"[012]", "0, 1, 2 のいずれかで入力してください", False, "error")
    check_regex("出荷予定日", r"\d{4}/\d{2}/\d{2}", "YYYY/MM/DD 形式で入力してください", False, "error")
    return errors, warnings

def build_yamato_df(common_df):
    yamato_df = pd.DataFrame(index=common_df.index)
    for col in YAMATO_FIELDS:
        yamato_df[col] = ""
    mapping_pairs = {"お客様管理番号": "受注番号", "送り状種類": "送り状種別", "クール区分": "温度帯", "出荷予定日": "出荷日", "お届け予定日": "指定日", "配達時間帯": "指定時間", "お届け先コード": "届け先コード", "お届け先電話番号": "届け先電話番号", "お届け先電話番号枝番": "届け先電話番号枝番", "お届け先郵便番号": "届け先郵便番号", "お届け先住所": "届け先住所1", "お届け先アパートマンション名": "届け先住所2", "お届け先名": "届け先名", "ご依頼主郵便番号": "ご依頼主郵便番号", "ご依頼主住所": "ご依頼主住所1", "ご依頼主名": "ご依頼主名", "品名１": "商品名1", "記事": "記事"}
    for y, c in mapping_pairs.items():
        yamato_df[y] = common_df.get(c, "")
    return yamato_df[YAMATO_FIELDS]

init_session()
inject_custom_style()
if not check_password():
    if st.session_state.get("authenticated", False):
        st.rerun()
    st.stop()

manager = TemplateManager()
selected_template = manager.render_selector_and_sync()

logout_col1, logout_col2 = st.columns([8, 1])
with logout_col2:
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

st.title("CSV/Excel マッピングツール（ダークテーマ安定版（テンプレ管理クラス版・安定版）")
rules_master = load_rules()
rule_names = ["（なし）"] + sorted(rules_master.keys())
gen = st.session_state["widget_gen"]

mode = st.selectbox("出力モード", ["通常モード", "ヤマト公式全列モード"], index=["通常モード", "ヤマト公式全列モード"].index(st.session_state["mode_model"]), key=f"mode_widget_{gen}")
st.session_state["mode_model"] = mode
if mode == "ヤマト公式全列モード":
    st.session_state["show_detail_model"] = True
show_detail = st.checkbox("詳細項目も表示する", value=st.session_state["show_detail_model"], disabled=(mode == "ヤマト公式全列モード"), key=f"show_detail_widget_{gen}")
st.session_state["show_detail_model"] = show_detail
show_transform_detail = st.checkbox("項目ごとの変換イメージ分析を表示する", value=st.session_state["show_transform_detail_model"], key=f"show_transform_detail_widget_{gen}")
st.session_state["show_transform_detail_model"] = show_transform_detail
available_fields = COMMON_FIELDS if (mode == "ヤマト公式全列モード" or show_detail) else BASIC_FIELDS

template_name_input = st.text_input("保存するテンプレート名", value="" if selected_template == manager.NEW_LABEL else selected_template, key=f"template_name_input_{gen}")
uploaded_file = st.file_uploader("ファイルを選択（CSV / Excel）", type=["csv", "xlsx"], key=f"uploader_{gen}")
df = None
columns = []
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()
    columns = list(df.columns)

st.subheader("変換ルール作成・編集")
rule_col1, rule_col2 = st.columns([2, 1])
with rule_col1:
    rule_target = st.selectbox("編集する変換ルール", ["（新規作成）"] + sorted(rules_master.keys()))
with rule_col2:
    new_rule_name = st.text_input("新規ルール名 / 保存名", value="" if rule_target == "（新規作成）" else rule_target)
if rule_target != st.session_state["last_rule_target"]:
    st.session_state["last_rule_target"] = rule_target
    if rule_target == "（新規作成）":
        st.session_state["rule_editor_rows"] = [{"変換前": "", "変換後": ""}]
    else:
        rule_dict = rules_master.get(rule_target, {})
        st.session_state["rule_editor_rows"] = [{"変換前": str(k), "変換後": str(v)} for k, v in rule_dict.items()] or [{"変換前": "", "変換後": ""}]
rule_editor_df = st.data_editor(pd.DataFrame(st.session_state["rule_editor_rows"]), num_rows="dynamic", use_container_width=True, key="rule_editor_df", hide_index=True)
st.session_state["rule_editor_rows"] = normalize_rule_rows(rule_editor_df)
rb1, rb2 = st.columns(2)
with rb1:
    if st.button("変換ルール保存"):
        name = new_rule_name.strip()
        if name == "":
            st.error("ルール名を入力してください")
        else:
            rules_master[name] = rule_rows_to_dict(st.session_state["rule_editor_rows"])
            save_rules(rules_master)
            st.success(f"変換ルール『{name}』を保存しました")
            st.rerun()
with rb2:
    if st.button("変換ルール削除"):
        if rule_target == "（新規作成）":
            st.error("削除するルールを選んでください")
        else:
            rules_master.pop(rule_target, None)
            save_rules(rules_master)
            st.success(f"変換ルール『{rule_target}』を削除しました")
            st.rerun()

st.subheader("テンプレート操作")
if st.session_state["template_save_message"]:
    st.success(st.session_state["template_save_message"])
    st.session_state["template_save_message"] = ""
if st.session_state["template_delete_message"]:
    st.success(st.session_state["template_delete_message"])
    st.session_state["template_delete_message"] = ""
tc1, tc2 = st.columns(2)
with tc1:
    if st.button("テンプレート保存"):
        name = template_name_input.strip()
        if name == "":
            st.error("テンプレート名を入力してください")
        else:
            manager.save_current_as(name)
with tc2:
    if st.button("テンプレート削除"):
        if selected_template == manager.NEW_LABEL:
            st.error("削除するテンプレートを選んでください")
        else:
            manager.delete_active(selected_template)

if df is not None:
    try:
        st.subheader("元データ")
        st.dataframe(df.head())
        st.subheader("項目設定")
        st.caption("各項目ごとに、入力列・固定値・変換ルールを設定できます")
        header_cols = st.columns([3,3,3,3])
        for idx, lbl in enumerate(["**項目名**","**入力列**","**固定値**","**変換ルール**"]):
            with header_cols[idx]: st.markdown(lbl)
        mapping = {}
        fixed_values = {}
        rule_selection = {}
        for field in available_fields:
            cols4 = st.columns([3,3,3,3])
            with cols4[0]: st.write(field)
            with cols4[1]:
                options = ["（未選択）","（空白）"] + columns
                cur = st.session_state["mapping_model"].get(field, "（未選択）")
                if cur not in options: cur = "（未選択）"
                val = st.selectbox(f"{field}_map", options, index=options.index(cur), label_visibility="collapsed", key=f"map_widget_{field}_{gen}")
                st.session_state["mapping_model"][field] = val
                mapping[field] = val
            with cols4[2]:
                val = st.text_input(f"{field}_fixed", value=st.session_state["fixed_values_model"].get(field, ""), label_visibility="collapsed", key=f"fixed_widget_{field}_{gen}")
                st.session_state["fixed_values_model"][field] = val
                fixed_values[field] = val
            with cols4[3]:
                cur_rule = st.session_state["rule_selection_model"].get(field, "（なし）")
                if cur_rule not in rule_names: cur_rule = "（なし）"
                val = st.selectbox(f"{field}_rule", rule_names, index=rule_names.index(cur_rule), label_visibility="collapsed", key=f"rule_widget_{field}_{gen}")
                st.session_state["rule_selection_model"][field] = val
                rule_selection[field] = val
        if mode == "通常モード":
            st.subheader("出力項目設定")
            st.caption("出力する項目を選んでください")
            selected_output_fields = []
            oc1, oc2 = st.columns(2)
            for i, field in enumerate(available_fields):
                with oc1 if i % 2 == 0 else oc2:
                    checked = st.checkbox(f"{field} を出力する", value=st.session_state["output_flags_model"].get(field, False), key=f"output_widget_{field}_{gen}")
                    st.session_state["output_flags_model"][field] = checked
                    if checked: selected_output_fields.append(field)
            current_order = [f for f in st.session_state["ordered_output_fields_model"] if f in selected_output_fields]
            for f in selected_output_fields:
                if f not in current_order: current_order.append(f)
            st.session_state["ordered_output_fields_model"] = current_order
            st.subheader("出力列名設定")
            rename_fields = {}
            rc1, rc2 = st.columns(2)
            for i, field in enumerate(available_fields):
                with rc1 if i % 2 == 0 else rc2:
                    val = st.text_input(f"{field} の出力列名", value=st.session_state["rename_fields_model"].get(field, field), key=f"rename_widget_{field}_{gen}")
                    st.session_state["rename_fields_model"][field] = val
                    rename_fields[field] = val
            st.subheader("出力順設定")
            st.caption("上へ / 下へ で並び替えできます")
            hh = st.columns([1,4,4,2])
            for c, lbl in zip(hh, ["**順番**","**項目名**","**出力列名**","**移動**"]):
                with c: st.markdown(lbl)
            for idx, field in enumerate(st.session_state["ordered_output_fields_model"], start=1):
                display_name = st.session_state["rename_fields_model"].get(field, field)
                c1, c2, c3, c4 = st.columns([1,4,4,2])
                with c1: st.markdown(f"**{idx}**")
                with c2: st.write(field)
                with c3: st.write(display_name)
                with c4:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("↑", key=f"up_{field}_{gen}"):
                            st.session_state["ordered_output_fields_model"] = move_item_up(st.session_state["ordered_output_fields_model"].copy(), field)
                            st.rerun()
                    with b2:
                        if st.button("↓", key=f"down_{field}_{gen}"):
                            st.session_state["ordered_output_fields_model"] = move_item_down(st.session_state["ordered_output_fields_model"].copy(), field)
                            st.rerun()
            ordered_output_fields = st.session_state["ordered_output_fields_model"].copy()
        else:
            ordered_output_fields = COMMON_FIELDS.copy()
            rename_fields = st.session_state["rename_fields_model"].copy()
            st.subheader("ヤマト公式全列モード")
            st.info("ヤマト公式の全列を固定順で出力します。使わない列も空欄で必ず出力します。")
        if st.button("変換実行"):
            common_df = pd.DataFrame(index=df.index)
            for field in COMMON_FIELDS:
                selected_col = mapping.get(field, "（未選択）")
                if selected_col == "（空白）":
                    common_df[field] = ""
                elif selected_col != "（未選択）":
                    common_df[field] = df[selected_col]
                else:
                    common_df[field] = ""
            common_df = common_df.fillna("")
            for col, val in fixed_values.items():
                if col in common_df.columns and str(val).strip() != "":
                    common_df[col] = str(val).strip()
            if "出荷日" in common_df.columns:
                common_df["出荷日"] = common_df["出荷日"].apply(format_date)
            if "指定日" in common_df.columns:
                common_df["指定日"] = common_df["指定日"].apply(format_date)
            for field, rule_name in rule_selection.items():
                if rule_name != "（なし）" and field in common_df.columns:
                    common_df[field] = apply_rule(common_df[field], rules_master.get(rule_name, {}))
            if mode == "通常モード":
                if len(ordered_output_fields) == 0:
                    st.error("出力項目を1つ以上選んでください")
                    st.stop()
                missing = [k for k in ordered_output_fields if st.session_state["output_flags_model"].get(k, False) and st.session_state["mapping_model"].get(k, "（未選択）") == "（未選択）" and str(st.session_state["fixed_values_model"].get(k, "")).strip() == ""]
                if missing:
                    st.error(f"未選択の項目があります: {', '.join(missing)}")
                    st.stop()
                output_df = common_df[ordered_output_fields].copy()
                rename_dict = {field: (str(st.session_state["rename_fields_model"].get(field, field)).strip() or field) for field in ordered_output_fields}
                output_df = output_df.rename(columns=rename_dict)
            else:
                output_df = build_yamato_df(common_df)
            st.success("変換完了！")
            st.subheader("変換後データ")
            st.dataframe(output_df)
            csv_data = output_df.to_csv(index=False, encoding="utf-8-sig")
            excel_data = to_excel_bytes(output_df)
            dc1, dc2 = st.columns(2)
            with dc1: st.download_button("CSVダウンロード", data=csv_data, file_name="output.csv", mime="text/csv")
            with dc2: st.download_button("Excelダウンロード", data=excel_data, file_name="output.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
