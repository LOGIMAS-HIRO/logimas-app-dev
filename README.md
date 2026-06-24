# FULL APP RESTORED - all previous functions retained
# corrected build: login/admin retained

import json
import re
import time
from io import BytesIO, StringIO
from pathlib import Path


# =========================================================
# Postgres永続保存レイヤー
# DATABASE_URL がある場合はPostgres保存、ない場合は従来保存
# =========================================================
import os
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

def _db_connect():
    if not USE_POSTGRES:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    except Exception as e:
        try:
            st.warning(f"Postgres接続に失敗しました。従来保存で動作します: {e}")
        except Exception:
            pass
        return None

def _db_init():
    conn = _db_connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS app_kv_store (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
        return True
    except Exception as e:
        try:
            st.warning(f"Postgres初期化に失敗しました。従来保存で動作します: {e}")
        except Exception:
            pass
        return False
    finally:
        conn.close()

def db_get(key, default=None):
    if not USE_POSTGRES or not _db_init():
        return default
    conn = _db_connect()
    if conn is None:
        return default
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM app_kv_store WHERE key=%s", (key,))
                row = cur.fetchone()
                return row[0] if row else default
    except Exception as e:
        try:
            st.warning(f"DB読込に失敗しました: {key} / {e}")
        except Exception:
            pass
        return default
    finally:
        conn.close()

def db_set(key, value):
    if not USE_POSTGRES or not _db_init():
        return False
    conn = _db_connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO app_kv_store (key, value, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (key)
                    DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
                """, (key, json.dumps(value, ensure_ascii=False)))
        return True
    except Exception as e:
        try:
            st.warning(f"DB保存に失敗しました: {key} / {e}")
        except Exception:
            pass
        return False
    finally:
        conn.close()

def db_delete(key):
    if not USE_POSTGRES or not _db_init():
        return False
    conn = _db_connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app_kv_store WHERE key=%s", (key,))
        return True
    except Exception:
        return False
    finally:
        conn.close()

def _df_to_records_for_db(df):
    try:
        return json.loads(df.fillna("").to_json(orient="records", force_ascii=False))
    except Exception:
        return []

def _records_to_df_for_db(records):
    try:
        import pandas as pd
        return pd.DataFrame(records or [])
    except Exception:
        return None

ASSETS_DIR = Path(__file__).parent / "assets"
PEEK_CHARACTER_IMAGE = ASSETS_DIR / "peek_character.png"

PEEK_ROBOT_IMAGE = ASSETS_DIR / "peek_robot.png"
LOGIN_LIGHT_BG_IMAGE = ASSETS_DIR / "login_light_bg.jpg"
LOGIN_ROBOT_IMAGE = ASSETS_DIR / "login_robot.jpg"
LOGIN_PANEL_IMAGE = ASSETS_DIR / "login_panel.jpg"
ROBOT_ICON_IMAGE = ASSETS_DIR / "robot_icon.png"
LOADING_RUN_IMAGE = ASSETS_DIR / "loading_run.jpg"
LOADING_PC_IMAGE = ASSETS_DIR / "loading_pc.jpg"
DASHBOARD_CONCEPT_IMAGE = ASSETS_DIR / "dashboard_concept.jpg"


# =========================================================
# 保存フォルダ定義
# Postgres利用時も、DATABASE_URL未設定時のフォールバック用に必要
# =========================================================
BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TEMPLATES_DIR = DATA_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

RULES_DIR = DATA_DIR / "rules"
RULES_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_MASTER_DIR = DATA_DIR / "product_master"
PRODUCT_MASTER_DIR.mkdir(parents=True, exist_ok=True)

PICKLIST_DIR = DATA_DIR / "picklist"
PICKLIST_DIR.mkdir(parents=True, exist_ok=True)

SHIPDATE_DIR = DATA_DIR / "shipdate"
SHIPDATE_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
RULES_FILE = DATA_DIR / "rules.json"

def asset_exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        return False

def render_asset(path: Path, caption: str = ""):
    if asset_exists(path):
        st.image(str(path), use_container_width=True, caption=caption if caption else None)
    else:
        st.info(f"画像ファイルが見つかりません: {path}")

def robot_icon_html():
    if asset_exists(ROBOT_ICON_IMAGE):
        import base64
        return f'<img src="data:image/png;base64,{base64.b64encode(ROBOT_ICON_IMAGE.read_bytes()).decode("ascii")}" class="v2-logo-img">'
    return '<span class="v2-logo-fallback">📦</span>'

def render_v2_topbar():
    st.markdown(
        f"""
        <div class="v2-topbar">
            <div class="v2-brand">{robot_icon_html()}<div><div class="v2-brand-title">出荷ラクっと Cloud</div><div class="v2-brand-sub">出荷前データ処理・帳票作成クラウド</div></div></div>
            <div class="v2-user-pill">👤 {st.session_state.get("user_display_name", st.session_state.get("user_id", ""))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )






def render_v2_login():
    import base64
    char_b64 = ""
    try:
        if PEEK_CHARACTER_IMAGE.exists():
            char_b64 = base64.b64encode(PEEK_CHARACTER_IMAGE.read_bytes()).decode("ascii")
    except Exception:
        char_b64 = ""

    char_html = ""
    if char_b64:
        char_html = f'<img class="true-peek-character" src="data:image/png;base64,{char_b64}">'

    st.markdown(
        f"""
        <style>
        /* ===== FINAL: 明るい白〜水色ログイン画面 ===== */
        html, body, .stApp {{
            background:
                radial-gradient(circle at 18% 12%, rgba(255,255,255,1), transparent 35%),
                radial-gradient(circle at 82% 8%, rgba(255,255,255,1), transparent 40%),
                linear-gradient(135deg, #ffffff 0%, #f6fbff 45%, #e4f1ff 100%) !important;
            color: #0f172a !important;
        }}
        .stApp::before, .login-bg-blur, .peek-robot, .mock-peek-robot {{
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }}
        .block-container {{
            padding-top: 1.2rem !important;
            max-width: 1500px !important;
            position: relative !important;
            z-index: 2 !important;
        }}
        .true-login-page::before {{
            content: "";
            position: fixed;
            left: 0; right: 0; bottom: 0;
            height: 38vh;
            background:
                radial-gradient(ellipse at 18% 100%, rgba(191,219,254,.48), transparent 58%),
                radial-gradient(ellipse at 76% 86%, rgba(224,242,254,.85), transparent 56%);
            z-index: 0;
            pointer-events: none;
        }}
        .true-brand {{
            text-align: center;
            margin-top: 28px;
            margin-bottom: 22px;
            position: relative;
            z-index: 4;
        }}
        .true-logo-main {{
            display: inline-flex;
            align-items: baseline;
            gap: 16px;
            position: relative;
        }}
        .true-logo-jp {{
            font-size: 68px;
            font-weight: 950;
            line-height: 1;
            letter-spacing: .03em;
            background: linear-gradient(135deg, #082c73 0%, #155ee6 58%, #20b8e8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 10px 22px rgba(37,99,235,.13));
        }}
        .true-logo-cloud {{
            font-size: 54px;
            font-weight: 900;
            font-style: italic;
            line-height: 1;
            background: linear-gradient(135deg, #2563eb, #21b8e8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .true-logo-main::after {{
            content: "✦";
            position: absolute;
            right: 185px;
            top: -28px;
            color: #22b6e9;
            font-size: 28px;
        }}
        .true-logo-cloudmark {{
            position: absolute;
            right: -74px;
            top: -18px;
            width: 88px;
            height: 52px;
            border: 7px solid #28a9e6;
            border-bottom-color: transparent;
            border-radius: 50px 50px 18px 18px;
            opacity: .9;
        }}
        .true-logo-swoosh {{
            width: 390px;
            height: 9px;
            margin: 12px auto 0 auto;
            background: linear-gradient(90deg, #1d4ed8, #22d3ee);
            clip-path: polygon(0 55%, 100% 0, 92% 45%, 10% 100%);
            opacity: .9;
        }}
        .true-subtitle {{
            margin-top: 20px;
            color: #64748b;
            font-weight: 850;
            letter-spacing: .08em;
            font-size: 16px;
        }}

        /* CSSの壁 + キャラだけ覗く */
        .true-peek-wrap {{
            position: fixed;
            right: 0;
            top: 36%;
            width: 230px;
            height: 360px;
            z-index: 8;
            pointer-events: none;
        }}
        .true-peek-wall {{
            position: absolute;
            right: 0;
            top: 0;
            width: 112px;
            height: 100%;
            background: #ffffff;
            border-left: 1px solid #e2e8f0;
            border-radius: 10px 0 0 10px;
            box-shadow: -14px 0 34px rgba(15,23,42,.08);
            z-index: 3;
        }}
        .true-peek-character {{
            position: absolute;
            right: 46px;
            top: 22px;
            width: 185px;
            z-index: 2;
            filter: drop-shadow(0 18px 32px rgba(15,23,42,.18));
            animation: truePeekMotion 5.4s ease-in-out infinite;
        }}
        @keyframes truePeekMotion {{
            0%, 18% {{ transform: translateX(62px) rotate(-3deg); opacity: .62; }}
            42%, 66% {{ transform: translateX(0) rotate(-1deg); opacity: 1; }}
            86%, 100% {{ transform: translateX(62px) rotate(-3deg); opacity: .62; }}
        }}

        /* ログインカードを添付に寄せる */
        .mock-login-card-head {{
            background: rgba(255,255,255,.90) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(203,213,225,.72) !important;
            border-bottom: none !important;
            border-radius: 28px 28px 0 0 !important;
            padding: 34px 48px 8px 48px !important;
            box-shadow: 0 20px 60px rgba(59,130,246,.14) !important;
            text-align: center !important;
        }}
        .mock-login-title {{
            color: #0b2f78 !important;
            font-size: 30px !important;
            font-weight: 950 !important;
            margin-bottom: 12px !important;
        }}
        .mock-login-desc {{
            color: #64748b !important;
            font-size: 15px !important;
            font-weight: 800 !important;
            margin-bottom: 24px !important;
        }}
        .mock-lock {{
            display: inline-flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 46px !important;
            height: 46px !important;
            border-radius: 50% !important;
            color: #2563eb !important;
            background: linear-gradient(135deg, #dbeafe, #eef6ff) !important;
            font-size: 22px !important;
            font-weight: 900 !important;
            margin-bottom: 8px !important;
        }}
        [data-testid="stForm"] {{
            background: rgba(255,255,255,.90) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(203,213,225,.72) !important;
            border-top: none !important;
            border-radius: 0 0 28px 28px !important;
            padding: 0 48px 34px 48px !important;
            box-shadow: 0 24px 60px rgba(59,130,246,.13) !important;
        }}
        [data-testid="stForm"] label,
        [data-testid="stForm"] p {{
            color: #0b2f78 !important;
            opacity: 1 !important;
            font-weight: 900 !important;
        }}
        [data-testid="stForm"] [data-testid="stTextInputRootElement"],
        [data-testid="stForm"] [data-baseweb="input"] {{
            background: rgba(255,255,255,.96) !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 13px !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }}
        [data-testid="stForm"] [data-baseweb="input"] > div {{
            background: transparent !important;
        }}
        [data-testid="stForm"] input {{
            background: transparent !important;
            color: #0f172a !important;
            border: none !important;
            min-height: 54px !important;
        }}
        [data-testid="stForm"] input::placeholder {{
            color: #94a3b8 !important;
            opacity: 1 !important;
        }}
        [data-testid="stForm"] button[kind="icon"],
        [data-testid="stForm"] [data-testid="stTextInputRootElement"] button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #64748b !important;
            width: auto !important;
            min-height: auto !important;
            margin: 0 !important;
        }}
        [data-testid="stFormSubmitButton"] button {{
            width: 100% !important;
            min-height: 62px !important;
            margin-top: 22px !important;
            border-radius: 18px !important;
            background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
            color: #ffffff !important;
            border: none !important;
            font-size: 18px !important;
            font-weight: 950 !important;
            box-shadow: 0 16px 32px rgba(37,99,235,.28) !important;
        }}
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span {{
            color: #ffffff !important;
            opacity: 1 !important;
        }}
        .mock-login-footer, .mock-divider, .mock-sso {{
            display: none !important;
        }}
        .block-container::after {{
            content: "© 2026 出荷ラクっと Cloud. All rights reserved.";
            display: block;
            text-align: center;
            color: #94a3b8;
            font-weight: 700;
            margin: 28px 0 8px 0;
        }}
        @media (max-width: 980px) {{
            .true-logo-jp {{ font-size: 42px; }}
            .true-logo-cloud {{ font-size: 34px; }}
            .true-logo-cloudmark, .true-logo-main::after {{ display: none; }}
            .true-logo-swoosh {{ width: 260px; }}
            .true-subtitle {{ font-size: 13px; }}
            .true-peek-wrap {{ display: none; }}
            [data-testid="stForm"], .mock-login-card-head {{
                padding-left: 28px !important;
                padding-right: 28px !important;
            }}
        }}
        </style>
        <div class="true-login-page">
            <div class="true-brand">
                <div class="true-logo-main">
                    <span class="true-logo-jp">出荷ラクっと</span>
                    <span class="true-logo-cloud">Cloud</span>
                    <span class="true-cloud-emoji">☁</span>
                </div>
                <div class="true-logo-swoosh"></div>
                <div class="true-subtitle">出荷前データ処理・帳票作成クラウド</div>
            </div>
            <div class="true-peek-wrap">
                {char_html}
                <div class="true-peek-wall"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _left, center, _right = st.columns([0.95, 0.95, 0.95])
    return center

def render_v2_dashboard_summary():
    try:
        owner = current_product_master_owner()
        ship_name = load_ship_date_store(owner).get("active_name", "（使用しない）")
        pick_name = load_picklist_mapping_store(owner).get("active_name", "未設定")
        pm_count = len(load_product_master_df(owner))
        rule_count = len(load_rules())
    except Exception:
        ship_name, pick_name, pm_count, rule_count = "（使用しない）", "未設定", 0, 0

    st.markdown('<div class="v2-section-title">ダッシュボード</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="v2-card"><div class="v2-card-label">商品マスタ</div><div class="v2-card-num">{pm_count}</div><div class="v2-card-sub">登録件数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="v2-card"><div class="v2-card-label">変換ルール</div><div class="v2-card-num">{rule_count}</div><div class="v2-card-sub">登録済み</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="v2-card"><div class="v2-card-label">出荷日ルール</div><div class="v2-card-num small">{ship_name}</div><div class="v2-card-sub">現在使用</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="v2-card"><div class="v2-card-label">帳票設定</div><div class="v2-card-num small">{pick_name}</div><div class="v2-card-sub">現在使用</div></div>', unsafe_allow_html=True)

def render_v2_quick_nav():
    st.markdown(
        """
        <div class="v2-quick">
            <div class="v2-quick-item">📄 CSV取込</div>
            <div class="v2-quick-item">🔄 データ変換</div>
            <div class="v2-quick-item">🔗 コード変換・統一</div>
            <div class="v2-quick-item">📅 出荷日計算</div>
            <div class="v2-quick-item">🧾 帳票出力</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_robot_loading(message: str = "処理中です…"):
    img = LOADING_RUN_IMAGE if asset_exists(LOADING_RUN_IMAGE) else LOADING_PC_IMAGE
    if asset_exists(img):
        st.image(str(img), width=180)
    st.markdown(
        f"""
        <div class="v2-loading"><div class="v2-loading-title">{message}</div><div class="v2-loading-bar"><span></span></div></div>
        """,
        unsafe_allow_html=True,
    )
import os

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

st.set_page_config(page_title="CSV/Excel マッピングツール", layout="wide")

TEMPLATE_DIR = Path("templates")
TEMPLATE_DIR.mkdir(exist_ok=True)
RULES_FILE = Path("rules.json")
RULES_DIR = Path("rules_store")
RULES_DIR.mkdir(exist_ok=True)
PRODUCT_MASTER_DIR = Path("product_master_store")
PRODUCT_MASTER_DIR.mkdir(exist_ok=True)
PICKLIST_MAPPING_DIR = Path("picklist_mapping_store")
PICKLIST_MAPPING_DIR.mkdir(exist_ok=True)
SHIP_DATE_SETTING_DIR = Path("ship_date_setting_store")
SHIP_DATE_SETTING_DIR.mkdir(exist_ok=True)
USERS_FILE = Path("users.json")
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


def inject_custom_style():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1120;
            --bg2: #111827;
            --line: rgba(148, 163, 184, 0.18);
            --text: #f8fafc;
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
        .block-container {
            padding-top: 3.6rem;
            padding-bottom: 2rem;
        }
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
        div.stButton > button, div.stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {
            border-radius: 999px !important;
            border: 1px solid rgba(148,163,184,0.22) !important;
            background: linear-gradient(135deg, var(--brand) 0%, var(--brand2) 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            padding: 0.58rem 1.14rem !important;
        }
        [data-testid="stCheckbox"] label, [data-testid="stCheckbox"] p, [data-testid="stRadio"] label, [data-testid="stFileUploaderDropzone"] * {
            color: var(--text) !important;
        }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stDataFrame"] > div, [data-testid="stDataEditor"] > div,
        [data-testid="stDataFrameGlideDataEditor"], [data-testid="stDataEditor"] [data-testid="stDataFrameGlideDataEditor"] {
            background: #ffffff !important;
            color: #ffffff !important;
            border: 1px solid rgba(148,163,184,0.20) !important;
            border-radius: 20px !important;
            overflow: hidden !important;
            --gdg-bg-cell: #ffffff;
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
        [data-testid="stDataFrame"] *, [data-testid="stDataEditor"] *, [data-testid="stDataFrameGlideDataEditor"] *, [data-testid="stDataEditor"] [data-testid="stDataFrameGlideDataEditor"] * {
            color: #ffffff !important;
        }
        [data-testid="stDataEditor"] input, [data-testid="stDataEditor"] textarea, [data-testid="stDataFrame"] input, [data-testid="stDataFrame"] textarea {
            background: #0f172a !important; color: #ffffff !important; caret-color: #ffffff !important; border: 1px solid rgba(148,163,184,0.22) !important;
        }
        [data-testid="stAlert"] { border-radius: 16px !important; border: 1px solid var(--line) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def default_users():
    return {
        "admin": {"password": APP_PASSWORD, "role": "admin", "display_name": "管理者"},
        "izumise": {"password": "pass1234", "role": "client", "display_name": "イズミセ"},
        "liquor": {"password": "pass5678", "role": "client", "display_name": "リカーマウンテン"},
    }

def ensure_users_file():
    if not USERS_FILE.exists():
        save_users(default_users())

def load_users():
    db_users = db_get("users", None)
    if db_users is not None:
        return db_users
    ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_users()

def save_users(users):
    if db_set("users", users):
        return
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def valid_user_id(user_id: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_\-]+", user_id or "") is not None


def show_login_processing():
    # ログイン後の下部アクション/ローディング表示は出さない
    return

def check_login():
    users = load_users()
    if st.session_state.get("authenticated", False):
        uid = st.session_state.get("user_id")
        if uid in users:
            return True

    login_right = render_v2_login()
    with login_right:
        st.markdown(
            """
            <div class="mock-login-card-head">
                <div class="mock-lock">▣</div>
                <div class="mock-login-title">ログイン</div>
                <div class="mock-login-desc">ユーザーIDとパスワードを入力してください</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            user_id = st.text_input("ユーザーID", placeholder="ユーザーIDを入力")
            pw = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
            submitted = st.form_submit_button("ログイン")

    if submitted:
        user = users.get(user_id.strip())
        if user and user.get("password") == pw:
            clear_runtime_state_for_logout()
            init_session()
            st.session_state["authenticated"] = True
            st.session_state["user_id"] = user_id.strip()
            st.session_state["user_role"] = user.get("role", "client")
            st.session_state["user_display_name"] = user.get("display_name", user_id.strip())
            set_rule_state("rule_edit_rows", [{"変換前": "", "変換後": ""}])
            set_rule_state("rule_edit_name", "")
            set_rule_state("last_rule_target", "（新規作成）")
            set_rule_state("pending_rule_target", "（新規作成）")
            set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
            show_login_processing()
            time.sleep(0.7)
            st.rerun()
        st.error("ユーザーIDまたはパスワードが違います。")
    return False

def user_prefix():
    role = st.session_state.get("user_role", "client")
    uid = st.session_state.get("user_id", "")
    return "" if role == "admin" else f"{uid}__"

def visible_template_name(stored_name):
    prefix = user_prefix()
    if prefix and stored_name.startswith(prefix):
        return stored_name[len(prefix):]
    return stored_name

def stored_template_name(visible_name):
    prefix = user_prefix()
    return f"{prefix}{visible_name}" if prefix else visible_name


def rule_prefix():
    return user_prefix()

def visible_rule_name(stored_name):
    prefix = rule_prefix()
    if prefix and stored_name.startswith(prefix):
        return stored_name[len(prefix):]
    return stored_name

def stored_rule_name(visible_name):
    prefix = rule_prefix()
    return f"{prefix}{visible_name}" if prefix else visible_name

def user_rule_state_key(base):
    uid = st.session_state.get("user_id", "guest")
    role = st.session_state.get("user_role", "client")
    return f"{base}__{role}__{uid}"

def get_rule_state(base, default):
    key = user_rule_state_key(base)
    if key not in st.session_state:
        import copy
        st.session_state[key] = copy.deepcopy(default)
    return st.session_state[key]

def set_rule_state(base, value):
    key = user_rule_state_key(base)
    st.session_state[key] = value


def clear_current_user_rule_editor_state():
    uid = st.session_state.get("user_id", "guest")
    role = st.session_state.get("user_role", "client")
    suffix = f"__{role}__{uid}"
    targets = [
        "rule_target_widget",
        "rule_edit_name",
        "rule_edit_rows",
        "last_rule_target",
        "pending_rule_target",
        "rule_saved_message",
        "rule_dirty",
    ]
    for base in targets:
        st.session_state.pop(f"{base}{suffix}", None)
    for k in list(st.session_state.keys()):
        if k.endswith(suffix) and (
            k.startswith("rule_form_before_")
            or k.startswith("rule_form_after_")
            or k.startswith("rule_before_")
            or k.startswith("rule_after_")
            or k.startswith("rule_del_")
            or k.startswith("rule_add_row_")
            or k.startswith("rule_name_input")
        ):
            st.session_state.pop(k, None)


def clear_runtime_state_for_logout():
    """ログアウト時に一時データだけ消す。保存済みファイル類は消さない。"""
    for k in list(st.session_state.keys()):
        # ログイン情報は最後に消す
        if k in ("authenticated", "user_id", "user_role", "user_display_name"):
            continue

        # 保存済みデータではなく、画面上の一時状態・アップロード・変換結果・PDF・フォーム系を消す
        if (
            k.startswith("converted_output_")
            or k.startswith("picklist_pdf_")
            or k.startswith("pick_")
            or k.startswith("product_master_")
            or k.startswith("template_")
            or k.startswith("rule_")
            or k.startswith("map_widget_")
            or k.startswith("fixed_widget_")
            or k.startswith("rule_widget_")
            or k.startswith("rename_widget_")
            or k.startswith("output_widget_")
            or k.startswith("uploader_")
            or k.startswith("product_master_uploader_")
            or k.startswith("picklist_")
            or k in (
                "config_loaded",
                "widget_gen",
                "mode_model",
                "show_detail_model",
                "show_transform_detail_model",
                "mapping_model",
                "fixed_values_model",
                "rule_selection_model",
                "rename_fields_model",
                "output_flags_model",
                "ordered_output_fields_model",
                "product_master_success_message",
                "picklist_mapping_success_message",
            )
        ):
            st.session_state.pop(k, None)

    for key in ("authenticated", "user_id", "user_role", "user_display_name"):
        st.session_state.pop(key, None)

def list_rule_names_for_user(rules_master):
    return sorted(rules_master.keys())


def rule_prefix():
    role = st.session_state.get("user_role", "client")
    uid = st.session_state.get("user_id", "")
    return "" if role == "admin" else f"{uid}__"

def visible_rule_name(stored_name):
    prefix = rule_prefix()
    if prefix and stored_name.startswith(prefix):
        return stored_name[len(prefix):]
    return stored_name

def stored_rule_name(visible_name):
    prefix = rule_prefix()
    return f"{prefix}{visible_name}" if prefix else visible_name

def list_templates():
    db_templates = db_get("templates", None)
    if db_templates is not None:
        return sorted(list(db_templates.keys()))

    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    if not templates_dir.exists():
        return []
    return sorted([p.stem for p in templates_dir.glob("*.json")])

def load_template(name):
    db_templates = db_get("templates", None)
    if db_templates is not None:
        return db_templates.get(name)
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def save_template(name, config):
    db_templates = db_get("templates", None)
    if db_templates is not None or USE_POSTGRES:
        db_templates = db_templates or {}
        db_templates[name] = config
        if db_set("templates", db_templates):
            return
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_template(name):
    db_templates = db_get("templates", None)
    if db_templates is not None:
        db_templates.pop(name, None)
        db_set("templates", db_templates)
        return
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
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
        "active_ship_date_setting": "（使用しない）",
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
        "rule_saved_message": "",
        "rule_dirty": False,
        "template_selector_widget": "（新規）",
        "user_admin_tab_index": 0,
        "user_add_success_message": "",
        "user_edit_success_message": "",
        "user_add_reset_counter": 0,
        "pending_clear_rule_inputs": False,
        "rule_form_reset_counter": 0,
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
    # テンプレート切替時は、前の変換結果・ピッキングPDF・アラートなどの一時データを消す
    for _k in list(st.session_state.keys()):
        if _k.startswith("converted_output_") or _k.startswith("picklist_pdf_") or _k == "ship_date_alerts":
            st.session_state.pop(_k, None)

    # テンプレート切替時は、変換ルール編集欄を新規作成に戻す
    try:
        clear_current_user_rule_editor_state()
        set_rule_state("rule_edit_rows", [{"変換前": "", "変換後": ""}])
        set_rule_state("rule_edit_name", "")
        set_rule_state("last_rule_target", "（新規作成）")
        set_rule_state("pending_rule_target", "（新規作成）")
        set_rule_state("rule_edit_type", "通常変換")
        set_rule_state("rule_lookup_from", "商品コード")
        set_rule_state("rule_lookup_to", "品名")
        set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
    except Exception:
        pass

    # テンプレートに紐づく出荷日設定を反映。新規テンプレートは「使用しない」に戻す。
    try:
        _owner = current_product_master_owner()
        _ship_store = load_ship_date_store(_owner)
        _active_ship = str(config.get("active_ship_date_setting", "（使用しない）") or "（使用しない）")
        if _active_ship != "（使用しない）" and _active_ship not in _ship_store.get("patterns", {}):
            _active_ship = "（使用しない）"
        _ship_store["active_name"] = _active_ship
        save_ship_date_store(_ship_store, _owner)
    except Exception:
        pass

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
        "active_ship_date_setting": load_ship_date_store(current_product_master_owner()).get("active_name", "（使用しない）"),
    }

class TemplateManager:
    NEW_LABEL = "（新規）"
    SELECTBOX_KEY = "template_selector_widget"

    def render_selector_and_sync(self):
        raw_options = list_templates()
        display_options = [self.NEW_LABEL] + [visible_template_name(x) for x in raw_options]

        pending = st.session_state.get("template_pending_name")
        if pending is not None:
            pending_display = self.NEW_LABEL if pending == self.NEW_LABEL else visible_template_name(pending)
            st.session_state[self.SELECTBOX_KEY] = pending_display if pending_display in display_options else self.NEW_LABEL
        elif st.session_state.get(self.SELECTBOX_KEY) not in display_options:
            st.session_state[self.SELECTBOX_KEY] = self.NEW_LABEL

        selected_display = st.selectbox("テンプレート選択", display_options, key=self.SELECTBOX_KEY)

        active_stored = st.session_state["template_active_name"]
        active_display = self.NEW_LABEL if active_stored == self.NEW_LABEL else visible_template_name(active_stored)

        if pending is None and selected_display != active_display:
            st.session_state["template_pending_name"] = self.NEW_LABEL if selected_display == self.NEW_LABEL else stored_template_name(selected_display)
            st.rerun()

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
            st.session_state["template_pending_name"] = None
            st.rerun()

        return active_display

    def save_current_as(self, visible_name):
        stored_name = stored_template_name(visible_name)
        save_template(stored_name, collect_config_from_models())
        st.session_state["template_save_message"] = f"テンプレート『{visible_name}』を保存しました"
        st.session_state["template_pending_name"] = stored_name
        st.session_state["template_active_name"] = stored_name
        st.rerun()

    def delete_active(self, visible_name):
        stored_name = stored_template_name(visible_name)
        delete_template(stored_name)
        st.session_state["template_delete_message"] = f"テンプレート『{visible_name}』を削除しました"
        st.session_state["template_pending_name"] = self.NEW_LABEL
        st.session_state["template_active_name"] = self.NEW_LABEL
        st.rerun()

def load_all_rules():
    if not RULES_FILE.exists():
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _read_rule_file_for(user_id: str):
    path = RULES_DIR / f"{user_id}.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _write_rule_file_for(user_id: str, data: dict):
    path = RULES_DIR / f"{user_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _migrate_legacy_rules_if_needed():
    # rules_store が空で rules.json があるときだけ一度移行
    has_rule_files = any(RULES_DIR.glob("*.json"))
    if has_rule_files or not RULES_FILE.exists():
        return
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            legacy = json.load(f)
        if not isinstance(legacy, dict):
            return
    except Exception:
        return

    grouped = {}
    for key, val in legacy.items():
        if "__" in key:
            uid, rule_name = key.split("__", 1)
        else:
            uid, rule_name = "__admin__", key
        grouped.setdefault(uid, {})[rule_name] = val

    for uid, rules in grouped.items():
        _write_rule_file_for(uid, rules)

def load_rules():
    db_rules = db_get("rules", None)
    if db_rules is not None:
        return db_rules
    return load_all_rules()

def save_rule_entry(name, payload):
    rules = load_rules()
    rules[name] = payload
    if db_set("rules", rules):
        return
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_rule_entry(name):
    rules = load_rules()
    rules.pop(name, None)
    if db_set("rules", rules):
        return
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

def clean_series(series):
    return series.astype(str).str.strip().replace("nan", "")

def format_date(value):
    """
    許可する日付パターン:
    - YYYY/MM/DD
    - YYYY-M-D / YYYY-MM-DD
    - YYYYMMDD
    - YYYY-MM-DD HH:MM:SS
    - pandas / Excel の日付型
    - Unix timestamp 秒 (10桁前後)
    - Unix timestamp ミリ秒 (13桁前後)
    - Excelシリアル値
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    value_str = str(value).strip()
    if value_str == "" or value_str.lower() in ["none", "nan", "nat"]:
        return ""

    # pandas timestamp / datetime
    if isinstance(value, (pd.Timestamp, )):
        try:
            return pd.to_datetime(value).strftime("%Y/%m/%d")
        except Exception:
            pass

    # まず通常の文字列日付を優先
    for parse_kwargs in [
        {},
        {"format": "%Y/%m/%d"},
        {"format": "%Y-%m-%d"},
        {"format": "%Y%m%d"},
        {"format": "%Y-%m-%d %H:%M:%S"},
        {"format": "%Y/%m/%d %H:%M:%S"},
    ]:
        try:
            dt = pd.to_datetime(value_str, **parse_kwargs)
            if not pd.isna(dt):
                return dt.strftime("%Y/%m/%d")
        except Exception:
            pass

    # 数値系の解釈
    try:
        num = float(value_str.replace(",", ""))
        # Unix timestamp ミリ秒
        if abs(num) >= 10**11:
            dt = pd.to_datetime(int(num), unit="ms")
            return dt.strftime("%Y/%m/%d")
        # Unix timestamp 秒
        if abs(num) >= 10**9:
            dt = pd.to_datetime(int(num), unit="s")
            return dt.strftime("%Y/%m/%d")
        # YYYYMMDD
        if float(num).is_integer():
            num_int_str = str(int(num))
            if len(num_int_str) == 8 and num_int_str.startswith(("19", "20")):
                dt = pd.to_datetime(num_int_str, format="%Y%m%d")
                return dt.strftime("%Y/%m/%d")
        # Excelシリアル値
        if 20000 <= num <= 80000:
            dt = pd.Timestamp("1899-12-30") + pd.to_timedelta(num, unit="D")
            return dt.strftime("%Y/%m/%d")
    except Exception:
        pass

    return value_str

def normalize_rule_definition(rule_data):
    if not isinstance(rule_data, dict):
        return {"type": "manual", "mapping": {}}
    if "__rule_type__" in rule_data:
        return {
            "type": "master_lookup" if rule_data.get("__rule_type__") == "master_lookup" else "manual",
            "mapping": rule_data.get("mapping", {}) if isinstance(rule_data.get("mapping", {}), dict) else {},
            "lookup_from": str(rule_data.get("lookup_from", "商品コード") or "商品コード"),
            "lookup_to": str(rule_data.get("lookup_to", "品名") or "品名"),
        }
    return {"type": "manual", "mapping": rule_data}

def build_master_lookup_map(lookup_from: str, lookup_to: str):
    pm_df = load_product_master_df(current_product_master_owner())
    if pm_df.empty or lookup_from not in pm_df.columns or lookup_to not in pm_df.columns:
        return {}
    temp = pm_df[[lookup_from, lookup_to]].copy().fillna("")
    temp[lookup_from] = temp[lookup_from].astype(str).str.strip()
    temp[lookup_to] = temp[lookup_to].astype(str).str.strip()
    temp = temp[temp[lookup_from] != ""]
    temp = temp.drop_duplicates(subset=[lookup_from], keep="last")
    return dict(zip(temp[lookup_from], temp[lookup_to]))

def get_rule_payload_by_name(rules_master, rule_name: str):
    if not rule_name or rule_name == "（なし）":
        return {}
    if rule_name in rules_master:
        return rules_master.get(rule_name, {})
    stored_name = stored_rule_name(rule_name)
    return rules_master.get(stored_name, {})


def parse_date_to_timestamp(value):
    formatted = format_date(value)
    if formatted == "" or str(formatted).lower() in ["none", "nan", "nat"]:
        return None
    try:
        dt = pd.to_datetime(formatted)
        if pd.isna(dt):
            return None
        return dt.normalize()
    except Exception:
        return None

SHIP_WEEKDAYS = {
    "月": 0,
    "火": 1,
    "水": 2,
    "木": 3,
    "金": 4,
    "土": 5,
    "日": 6,
}

def ship_setting_path_for(owner: str):
    return SHIP_DATE_SETTING_DIR / f"{owner}.json"

def default_ship_date_setting():
    return {
        "days_before": 2,
        "blank_due_days_after_today": 1,
        "closed_weekdays": ["日"],
        "closed_dates": "",
        "holiday_mode": "さらに前日にずらす",
        "blank_due_holiday_mode": "翌営業日にする",
        "existing_ship_date_mode": "既存の出荷日は残す",
        "same_day_alert": True,
    }

def default_ship_date_store():
    return {"active_name": "（使用しない）", "patterns": {}}

def load_ship_date_store(owner):
    key = f"ship_date_store::{owner}"
    db_val = db_get(key, None)
    if db_val is not None:
        return db_val
    path = ship_setting_path_for(owner)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default_ship_date_store()

def save_ship_date_store(owner, store):
    key = f"ship_date_store::{owner}"
    if db_set(key, store):
        return
    path = ship_setting_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

def save_ship_date_setting(name: str, cfg: dict, owner: str | None = None, make_active: bool = True):
    name = str(name or "").strip()
    if name == "" or name == "（新規設定）" or name == "（使用しない）":
        raise ValueError("出荷日設定名を入力してください。")
    store = load_ship_date_store(owner)
    base = default_ship_date_setting()
    base.update(cfg)
    store["patterns"][name] = base
    if make_active:
        store["active_name"] = name
    save_ship_date_store(store, owner)

def delete_ship_date_setting(name: str, owner: str | None = None):
    store = load_ship_date_store(owner)
    if name in store.get("patterns", {}):
        del store["patterns"][name]
    if store.get("active_name") == name:
        store["active_name"] = "（使用しない）"
    save_ship_date_store(store, owner)

def load_ship_date_setting(owner: str | None = None, pattern_name: str | None = None):
    store = load_ship_date_store(owner)
    name = pattern_name or store.get("active_name", "（使用しない）")
    return store.get("patterns", {}).get(name)

def parse_closed_dates(text: str):
    dates = set()
    for raw in str(text or "").replace(",", "\n").replace("、", "\n").splitlines():
        s = raw.strip()
        if not s:
            continue
        dt = parse_date_to_timestamp(s)
        if dt is not None:
            dates.add(dt.date())
    return dates

def is_ship_closed_day(dt, cfg: dict):
    if dt is None:
        return False
    closed_weekdays = cfg.get("closed_weekdays", [])
    closed_nums = {SHIP_WEEKDAYS[w] for w in closed_weekdays if w in SHIP_WEEKDAYS}
    closed_dates = parse_closed_dates(cfg.get("closed_dates", ""))
    return dt.weekday() in closed_nums or dt.date() in closed_dates

def move_to_previous_business_day(dt, cfg: dict):
    if dt is None:
        return None
    while is_ship_closed_day(dt, cfg):
        dt = dt - pd.Timedelta(days=1)
    return dt

def move_to_next_business_day(dt, cfg: dict):
    if dt is None:
        return None
    while is_ship_closed_day(dt, cfg):
        dt = dt + pd.Timedelta(days=1)
    return dt

def calc_ship_date_from_due_date(due_value, cfg: dict):
    today = pd.Timestamp.today().normalize()
    due_dt = parse_date_to_timestamp(due_value)
    alerts = []

    if due_dt is None:
        base_days = int(cfg.get("blank_due_days_after_today", 1) or 0)
        candidate = today + pd.Timedelta(days=base_days)
        basis = "指定日空白"
    else:
        days_before = int(cfg.get("days_before", 2) or 0)
        candidate = due_dt - pd.Timedelta(days=days_before)
        basis = "指定日あり"

    original_candidate = candidate

    if is_ship_closed_day(candidate, cfg):
        if due_dt is None:
            blank_mode = cfg.get("blank_due_holiday_mode", "翌営業日にする")
            if blank_mode == "当日にする":
                candidate = today
                if is_ship_closed_day(candidate, cfg):
                    alerts.append(f"指定日空白: 仮出荷日 {original_candidate.strftime('%Y/%m/%d')} が休業日のため当日 {candidate.strftime('%Y/%m/%d')} にしました。")
            elif blank_mode == "前営業日にする":
                candidate = move_to_previous_business_day(candidate, cfg)
            else:
                candidate = move_to_next_business_day(candidate, cfg)
        else:
            holiday_mode = cfg.get("holiday_mode", "さらに前日にずらす")
            if holiday_mode == "指定日の前日にする":
                candidate = due_dt - pd.Timedelta(days=1)
                candidate = move_to_previous_business_day(candidate, cfg)
            else:
                candidate = move_to_previous_business_day(candidate, cfg)
        alerts.append(f"{basis}: 仮出荷日 {original_candidate.strftime('%Y/%m/%d')} が休業日のため {candidate.strftime('%Y/%m/%d')} に調整しました。")

    if bool(cfg.get("same_day_alert", True)) and candidate <= today:
        alerts.append(f"当日出荷アラート: 出荷日が {candidate.strftime('%Y/%m/%d')} です。")

    return candidate.strftime("%Y/%m/%d"), alerts

def apply_ship_date_setting_to_df(common_df: pd.DataFrame, cfg: dict):
    alerts = []
    if cfg is None:
        return common_df, alerts
    if "指定日" not in common_df.columns:
        common_df["指定日"] = ""
    if "出荷日" not in common_df.columns:
        common_df["出荷日"] = ""

    existing_mode = cfg.get("existing_ship_date_mode", "空白だけ自動計算")
    results = []
    for idx, v in common_df["指定日"].items():
        existing_ship = common_df.at[idx, "出荷日"]
        existing_ship_fmt = format_date(existing_ship)
        if existing_mode == "既存の出荷日は残す" and str(existing_ship_fmt).strip() != "":
            results.append(existing_ship_fmt)
            continue
        ship_date, row_alerts = calc_ship_date_from_due_date(v, cfg)
        results.append(ship_date)
        alerts.extend(row_alerts)
    common_df["出荷日"] = results
    alerts = list(dict.fromkeys(alerts))
    return common_df, alerts

def apply_rule(series, rule_data):
    rule_def = normalize_rule_definition(rule_data)
    cleaned = clean_series(series)
    if rule_def["type"] == "master_lookup":
        lookup_map = build_master_lookup_map(rule_def["lookup_from"], rule_def["lookup_to"])
        if not lookup_map:
            return cleaned
        return cleaned.map(lookup_map).fillna(cleaned)
    mapping = rule_def.get("mapping", {})
    if not mapping:
        return cleaned
    return cleaned.map(mapping).fillna(cleaned)

def extract_editor_rows(df_rule):
    if df_rule is None or len(df_rule) == 0:
        return [{"変換前": "", "変換後": ""}]
    rows = []
    for _, row in df_rule.iterrows():
        before = "" if pd.isna(row.get("変換前", "")) else str(row.get("変換前", ""))
        after = "" if pd.isna(row.get("変換後", "")) else str(row.get("変換後", ""))
        rows.append({"変換前": before, "変換後": after})
    if not rows:
        rows = [{"変換前": "", "変換後": ""}]
    # 最後に空行を必ず1行持たせる
    if rows[-1]["変換前"] != "" or rows[-1]["変換後"] != "":
        rows.append({"変換前": "", "変換後": ""})
    return rows

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


@st.cache_data(show_spinner=False)
def read_uploaded_file_cached(file_bytes: bytes, filename: str):
    from io import BytesIO as _BytesIO
    bio = _BytesIO(file_bytes)
    if filename.lower().endswith(".csv"):
        encodings = ["utf-8-sig", "cp932", "shift_jis", "utf-8", "latin1"]
        last_error = None
        for enc in encodings:
            try:
                bio.seek(0)
                df = pd.read_csv(bio, encoding=enc)
                break
            except Exception as e:
                last_error = e
        else:
            raise last_error
    else:
        bio.seek(0)
        df = pd.read_excel(bio)
    df.columns = df.columns.astype(str).str.strip()
    return df

@st.cache_data(show_spinner=False)
def dataframe_to_csv_cached(df: pd.DataFrame):
    return df.to_csv(index=False, encoding="utf-8-sig")

@st.cache_data(show_spinner=False)
def dataframe_to_excel_cached(df: pd.DataFrame):
    return to_excel_bytes(df)

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
        rule_dict = get_rule_payload_by_name(rules_master, rule_name) if rule_name != "（なし）" else {}
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


def collect_current_rule_rows():
    rows = get_rule_state("rule_editor_rows", [{"変換前": "", "変換後": ""}])
    collected = []
    for i in range(len(rows)):
        before_key = user_rule_state_key(f"rule_before_{i}")
        after_key = user_rule_state_key(f"rule_after_{i}")
        before_val = st.session_state.get(before_key, rows[i].get("変換前", ""))
        after_val = st.session_state.get(after_key, rows[i].get("変換後", ""))
        if str(before_val).strip() != "" or str(after_val).strip() != "":
            collected.append({"変換前": str(before_val), "変換後": str(after_val)})
    if not collected:
        collected = [{"変換前": "", "変換後": ""}]
    return collected

def clear_rule_input_widgets():
    uid = st.session_state.get("user_id", "guest")
    role = st.session_state.get("user_role", "client")
    suffix = f"__{role}__{uid}"
    for k in list(st.session_state.keys()):
        if k.startswith("rule_before_") and k.endswith(suffix):
            st.session_state.pop(k, None)
        if k.startswith("rule_after_") and k.endswith(suffix):
            st.session_state.pop(k, None)

PRODUCT_MASTER_COLUMNS = ["商品コード", "品名", "入数", "温度帯", "備考"]

def current_product_master_owner():
    role = st.session_state.get("user_role", "client")
    uid = st.session_state.get("user_id", "")
    return "__admin__" if role == "admin" else uid


PICKLIST_MAPPING_FIELDS = [
    ("受注番号", False),
    ("出荷日", True),
    ("指定日", True),
    ("指定時間", True),
    ("依頼主名", False),
    ("届け先名", False),
    ("商品コード", False),
    ("商品名", False),
    ("数量", False),
    ("熨斗", True),
    ("包装", True),
    ("その他", True),
]

def picklist_mapping_path_for(owner: str):
    return PICKLIST_MAPPING_DIR / f"{owner}.json"

def default_picklist_mapping():
    return {field: {"source": "（空白）", "fixed": ""} for field, _ in PICKLIST_MAPPING_FIELDS}

def default_picklist_mapping_store():
    return {"active_name": "（新規設定）", "patterns": {}}

def load_picklist_mapping_store(owner):
    key = f"picklist_mapping_store::{owner}"
    db_val = db_get(key, None)
    if db_val is not None:
        return db_val
    path = picklist_mapping_path_for(owner)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default_picklist_mapping_store()

def save_picklist_mapping_store(owner, store):
    key = f"picklist_mapping_store::{owner}"
    if db_set(key, store):
        return
    path = picklist_mapping_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

def load_picklist_mapping(owner: str | None = None, pattern_name: str | None = None):
    store = load_picklist_mapping_store(owner)
    name = pattern_name or store.get("active_name", "（新規設定）")
    return store.get("patterns", {}).get(name, default_picklist_mapping())

def save_picklist_mapping(mapping: dict, owner: str | None = None, pattern_name: str | None = None, make_active: bool = True):
    store = load_picklist_mapping_store(owner)
    name = str(pattern_name or store.get("active_name", "（新規設定）") or "（新規設定）").strip()
    if name == "" or name == "（新規設定）":
        raise ValueError("保存する設定名を入力してください。")
    store["patterns"][name] = {
        field: {
            "source": str(mapping.get(field, {}).get("source", "（空白）") or "（空白）"),
            "fixed": str(mapping.get(field, {}).get("fixed", "") or ""),
        }
        for field, _ in PICKLIST_MAPPING_FIELDS
    }
    if make_active:
        store["active_name"] = name
    save_picklist_mapping_store(store, owner)

def delete_picklist_mapping(owner: str | None = None, pattern_name: str | None = None):
    store = load_picklist_mapping_store(owner)
    name = str(pattern_name or "").strip()
    if name and name in store.get("patterns", {}):
        del store["patterns"][name]
        if store.get("active_name") == name:
            store["active_name"] = "（新規設定）"
        save_picklist_mapping_store(store, owner)
def product_master_path_for(owner: str):
    return PRODUCT_MASTER_DIR / f"{owner}.json"

def load_product_master_df(owner):
    key = f"product_master::{owner}"
    db_records = db_get(key, None)
    if db_records is not None:
        df = _records_to_df_for_db(db_records)
        if df is not None:
            return normalize_product_master_df(df)
    path = product_master_path_for(owner)
    if path.exists():
        try:
            import pandas as pd
            return normalize_product_master_df(pd.read_csv(path, dtype=str).fillna(""))
        except Exception:
            pass
    import pandas as pd
    return normalize_product_master_df(pd.DataFrame())

def save_product_master_df(owner, df):
    key = f"product_master::{owner}"
    records = _df_to_records_for_db(normalize_product_master_df(df))
    if db_set(key, records):
        return
    path = product_master_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalize_product_master_df(df).to_csv(path, index=False, encoding="utf-8-sig")

def merge_product_master_df(existing_df: pd.DataFrame, incoming_df: pd.DataFrame):
    existing = existing_df.copy()
    incoming = incoming_df.copy()

    for col in PRODUCT_MASTER_COLUMNS:
        if col not in existing.columns:
            existing[col] = ""
        if col not in incoming.columns:
            incoming[col] = ""

    existing = existing[PRODUCT_MASTER_COLUMNS].fillna("")
    incoming = incoming[PRODUCT_MASTER_COLUMNS].fillna("")

    existing["商品コード"] = existing["商品コード"].astype(str).str.strip()
    incoming["商品コード"] = incoming["商品コード"].astype(str).str.strip()

    existing_map = {str(row["商品コード"]).strip(): row.to_dict() for _, row in existing.iterrows() if str(row["商品コード"]).strip() != ""}
    add_count = 0
    update_count = 0

    for _, row in incoming.iterrows():
        code = str(row["商品コード"]).strip()
        if code == "":
            continue
        row_dict = row.to_dict()
        if code in existing_map:
            existing_map[code] = row_dict
            update_count += 1
        else:
            existing_map[code] = row_dict
            add_count += 1

    merged_df = pd.DataFrame(list(existing_map.values()))
    if merged_df.empty:
        merged_df = pd.DataFrame(columns=PRODUCT_MASTER_COLUMNS)
    else:
        merged_df = merged_df[PRODUCT_MASTER_COLUMNS].fillna("")
        merged_df = merged_df.sort_values(by=["商品コード"], kind="stable").reset_index(drop=True)

    return merged_df, add_count, update_count

def normalize_product_master_df(df: pd.DataFrame):
    normalized = df.copy()

    def clean_col_name(v):
        s = str(v)
        s = s.replace("\ufeff", "")
        s = s.replace("\u3000", " ")
        s = s.replace("\r", " ").replace("\n", " ")
        s = s.strip()
        s = re.sub(r"\s+", "", s)
        return s

    expected = PRODUCT_MASTER_COLUMNS
    alias_map = {
        "商品コード": "商品コード",
        "コード": "商品コード",
        "品番": "商品コード",
        "JAN": "商品コード",
        "JANコード": "商品コード",
        "品名": "品名",
        "商品名": "品名",
        "名称": "品名",
        "入数": "入数",
        "ケース入数": "入数",
        "温度帯": "温度帯",
        "温度": "温度帯",
        "備考": "備考",
        "メモ": "備考",
    }

    raw_cols = [clean_col_name(c) for c in normalized.columns.tolist()]

    # ヘッダーなし5列CSV対応
    if list(normalized.columns) == list(range(len(normalized.columns))) and len(normalized.columns) >= 5:
        normalized = normalized.iloc[:, :5].copy()
        normalized.columns = expected
    else:
        renamed_cols = [alias_map.get(c, c) for c in raw_cols]
        normalized.columns = renamed_cols

        # 主要列が見つからないが5列以上あるなら先頭5列を想定マスタとして扱う
        if not all(col in normalized.columns for col in ["商品コード", "品名", "入数"]):
            if len(normalized.columns) >= 5:
                normalized = normalized.iloc[:, :5].copy()
                normalized.columns = expected

    for col in PRODUCT_MASTER_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""

    normalized = normalized[PRODUCT_MASTER_COLUMNS].fillna("")
    normalized["商品コード"] = normalized["商品コード"].astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    normalized["品名"] = normalized["品名"].astype(str).str.strip()
    normalized["温度帯"] = normalized["温度帯"].astype(str).str.strip()
    normalized["備考"] = normalized["備考"].astype(str).str.strip()

    def parse_iri(val):
        s = str(val).strip()
        if s == "":
            return ""
        try:
            n = float(s)
            if n <= 0:
                return ""
            return int(n)
        except Exception:
            return ""

    normalized["入数"] = normalized["入数"].apply(parse_iri)
    normalized = normalized[normalized["商品コード"] != ""].copy()
    normalized = normalized.drop_duplicates(subset=["商品コード"], keep="last")
    return normalized.reset_index(drop=True)

def validate_product_master_df(df: pd.DataFrame):
    errors = []
    if "商品コード" not in df.columns:
        errors.append("商品コード列がありません。")
    if "品名" not in df.columns:
        errors.append("品名列がありません。")
    if "入数" not in df.columns:
        errors.append("入数列がありません。")
    if errors:
        return errors

    code_blank = df["商品コード"].astype(str).str.strip() == ""
    if code_blank.any():
        errors.append("商品コードが空の行があります。")
    iri_blank = pd.Series([str(v).strip() == "" for v in df["入数"]])
    if iri_blank.any():
        errors.append("入数が空または不正な行があります。")
    return errors


def format_quantity_display(value):
    try:
        if value is None:
            return ""
        if pd.isna(value):
            return ""
    except Exception:
        pass

    s = str(value).strip()
    if s == "" or s.lower() in ["none", "nan"]:
        return ""
    try:
        num = float(str(value).replace(",", ""))
        if num.is_integer():
            return str(int(num))
        return str(num)
    except Exception:
        return s

def build_picklist_dataframe(processed_df: pd.DataFrame, product_master_df: pd.DataFrame, picklist_mapping: dict | None = None):
    work = processed_df.copy()
    work.columns = work.columns.astype(str).str.strip()

    picklist_mapping = picklist_mapping or default_picklist_mapping()

    mapped = pd.DataFrame(index=work.index)

    for field, optional in PICKLIST_MAPPING_FIELDS:
        source = str(picklist_mapping.get(field, {}).get("source", "（空白）") or "（空白）")
        fixed = str(picklist_mapping.get(field, {}).get("fixed", "") or "").strip()

        if fixed != "":
            mapped[field] = fixed
        elif source not in ["（空白）", "（未選択）", ""]:
            if source in work.columns:
                mapped[field] = work[source]
            else:
                raise ValueError(f"ピッキング設定の列が見つかりません: {field} → {source}")
        else:
            mapped[field] = ""

    required_input_cols = ["受注番号", "依頼主名", "届け先名", "商品コード", "商品名", "数量"]
    missing_input = [c for c in required_input_cols if c not in mapped.columns or mapped[c].astype(str).str.strip().eq("").all()]
    if missing_input:
        raise ValueError(f"ピッキング設定の必須項目が不足しています: {', '.join(missing_input)}")

    work = mapped.copy()
    for col in work.columns:
        work[col] = work[col].fillna("").astype(str).replace(["None", "nan", "NaN"], "")

    # 完全空行や主要項目未入力行は除外
    keep_mask = ~(
        work["受注番号"].astype(str).str.strip().eq("") &
        work["商品コード"].astype(str).str.strip().eq("") &
        work["商品名"].astype(str).str.strip().eq("") &
        work["数量"].astype(str).str.strip().eq("")
    )
    work = work.loc[keep_mask].copy()

    for optional_col in ["熨斗", "包装", "その他"]:
        if optional_col not in work.columns:
            work[optional_col] = ""

    warnings = []

    master = product_master_df.copy()
    if master.empty:
        warnings.append("商品マスタが未登録のため、商品名は変換後データの値を使用し、温度帯・伝票枚数は空白で出力します。")
        master = pd.DataFrame(columns=PRODUCT_MASTER_COLUMNS)
    else:
        master["商品コード"] = master["商品コード"].astype(str).str.strip()

    work["商品コード"] = work["商品コード"].astype(str).str.strip()

    merged = work.merge(master, on="商品コード", how="left", suffixes=("", "_master"))

    merged["数量_raw"] = merged["数量"].astype(str).str.replace(",", "", regex=False).str.strip()
    merged["数量_num"] = pd.to_numeric(merged["数量_raw"], errors="coerce")

    bad_qty_df = merged.loc[
        merged["数量_num"].isna() &
        (
            merged["商品コード"].astype(str).str.strip().ne("") |
            merged["数量_raw"].astype(str).str.strip().ne("")
        )
    ]
    bad_qty = bad_qty_df["商品コード"].fillna("").astype(str).unique().tolist()
    if len(bad_qty_df) > 0:
        bad_qty_display = [x for x in bad_qty if x.strip() != ""]
        if bad_qty_display:
            raise ValueError("数量が数値でない商品コードがあります: " + ", ".join(map(str, bad_qty_display[:20])))
        else:
            raise ValueError("数量が数値でない行があります。数量列の値を確認してください。")

    merged["入数_num"] = pd.to_numeric(merged["入数"], errors="coerce")

    missing_codes = sorted(
        merged.loc[
            merged["入数_num"].isna() | (merged["入数_num"] <= 0),
            "商品コード"
        ].dropna().astype(str).unique().tolist()
    )
    if missing_codes:
        warnings.append("商品マスタ未登録または入数未設定の商品コードがあります: " + ", ".join(map(str, missing_codes[:20])))

    import math
    def calc_slip_count_safe(qty, iri):
        try:
            if pd.isna(iri) or iri <= 0 or pd.isna(qty):
                return ""
            return int(math.ceil(float(qty) / float(iri)))
        except Exception:
            return ""

    merged["伝票枚数"] = merged.apply(lambda r: calc_slip_count_safe(r["数量_num"], r["入数_num"]), axis=1)
    merged["備考"] = merged.apply(
        lambda r: " / ".join([
            f"熨斗: {str(r['熨斗']).strip()}" if str(r["熨斗"]).strip() else "",
            f"包装: {str(r['包装']).strip()}" if str(r["包装"]).strip() else "",
            f"その他: {str(r['その他']).strip()}" if str(r["その他"]).strip() else "",
        ]).strip(" /"),
        axis=1
    )

    if "温度帯" not in merged.columns:
        merged["温度帯"] = ""
    else:
        merged["温度帯"] = merged["温度帯"].fillna("").astype(str)

    if "商品名" not in merged.columns:
        merged["商品名"] = ""
    merged["商品名"] = merged["商品名"].fillna("").astype(str)

    if "品名" not in merged.columns:
        merged["品名"] = ""
    merged["品名"] = merged["品名"].fillna("").astype(str)

    merged["品名出力"] = merged.apply(
        lambda r: str(r["品名"]).strip() if str(r["品名"]).strip() not in ["", "nan", "None"] else str(r["商品名"]).strip(),
        axis=1
    )

    cols = ["受注番号", "出荷日", "指定日", "指定時間", "依頼主名", "届け先名", "商品コード", "品名出力", "数量", "伝票枚数", "温度帯", "備考"]
    out = merged[cols].copy()
    out = out.rename(columns={"品名出力": "商品名"})
    out["数量"] = out["数量"].apply(format_quantity_display)
    out["商品コード_sort"] = pd.to_numeric(out["商品コード"], errors="coerce")
    out = out.sort_values(["受注番号", "商品コード_sort", "商品コード"], kind="stable").drop(columns=["商品コード_sort"])
    return out.reset_index(drop=True), warnings


def build_picklist_pdf_bytes(picklist_df: pd.DataFrame):
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "jp_title",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1f2937"),
    )
    normal_style = ParagraphStyle(
        "jp_normal",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#111827"),
    )
    small_style = ParagraphStyle(
        "jp_small",
        parent=styles["Normal"],
        fontName="HeiseiKakuGo-W5",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#111827"),
    )

    story = []
    grouped = picklist_df.groupby("受注番号", sort=False)

    group_list = list(grouped)
    for page_idx, (order_no, grp) in enumerate(group_list):
        first = grp.iloc[0]

        story.append(Paragraph("ピッキングリスト", title_style))
        story.append(Spacer(1, 3 * mm))

        header_data = [
            [Paragraph("受注番号", normal_style), Paragraph(str(first.get("受注番号", "")), normal_style),
             Paragraph("出荷日", normal_style), Paragraph(str(first.get("出荷日", "")), normal_style),
             Paragraph("指定日", normal_style), Paragraph(str(first.get("指定日", "")), normal_style),
             Paragraph("指定時間", normal_style), Paragraph(str(first.get("指定時間", "")), normal_style)],
            [Paragraph("依頼主名", normal_style), Paragraph(str(first.get("依頼主名", "")), normal_style),
             Paragraph("届け先名", normal_style), Paragraph(str(first.get("届け先名", "")), normal_style),
             Paragraph("件数", normal_style), Paragraph(str(len(grp)), normal_style),
             Paragraph("", normal_style), Paragraph("", normal_style)],
        ]
        header_table = Table(header_data, colWidths=[18*mm, 52*mm, 18*mm, 52*mm, 18*mm, 28*mm, 18*mm, 28*mm])
        header_table.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "HeiseiKakuGo-W5"),
            ("FONTSIZE", (0,0), (-1,-1), 8.5),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#e5edf7")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#e5edf7")),
            ("BACKGROUND", (4,0), (4,-1), colors.HexColor("#e5edf7")),
            ("BACKGROUND", (6,0), (6,-1), colors.HexColor("#e5edf7")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 4 * mm))

        detail_data = [[
            Paragraph("商品コード", normal_style),
            Paragraph("商品名", normal_style),
            Paragraph("数量", normal_style),
            Paragraph("伝票枚数", normal_style),
            Paragraph("温度帯", normal_style),
            Paragraph("備考", normal_style),
        ]]

        for _, row in grp.iterrows():
            detail_data.append([
                Paragraph(str(row.get("商品コード", "")), small_style),
                Paragraph(str(row.get("商品名", "")), small_style),
                Paragraph(str(row.get("数量", "")), small_style),
                Paragraph(str(row.get("伝票枚数", "")), small_style),
                Paragraph(str(row.get("温度帯", "")), small_style),
                Paragraph(str(row.get("備考", "")), small_style),
            ])

        detail_table = Table(
            detail_data,
            repeatRows=1,
            colWidths=[28*mm, 78*mm, 18*mm, 22*mm, 18*mm, 98*mm],
        )
        detail_table.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "HeiseiKakuGo-W5"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dbe7f4")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(detail_table)

        if page_idx < len(group_list) - 1:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
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
    mapping_pairs = {
        "お客様管理番号": "受注番号", "送り状種類": "送り状種別", "クール区分": "温度帯", "出荷予定日": "出荷日",
        "お届け予定日": "指定日", "配達時間帯": "指定時間", "お届け先コード": "届け先コード",
        "お届け先電話番号": "届け先電話番号", "お届け先電話番号枝番": "届け先電話番号枝番", "お届け先郵便番号": "届け先郵便番号",
        "お届け先住所": "届け先住所1", "お届け先アパートマンション名": "届け先住所2", "お届け先名": "届け先名",
        "ご依頼主郵便番号": "ご依頼主郵便番号", "ご依頼主住所": "ご依頼主住所1", "ご依頼主名": "ご依頼主名",
        "品名１": "商品名1", "記事": "記事"
    }
    for y, c in mapping_pairs.items():
        yamato_df[y] = common_df.get(c, "")
    return yamato_df[YAMATO_FIELDS]

def render_admin_user_management():
    if st.session_state.get("user_role") != "admin":
        return

    st.subheader("ユーザー管理（管理者のみ）")

    if st.session_state.get("user_add_success_message"):
        st.success(st.session_state["user_add_success_message"])
        st.session_state["user_add_success_message"] = ""
    if st.session_state.get("user_edit_success_message"):
        st.success(st.session_state["user_edit_success_message"])
        st.session_state["user_edit_success_message"] = ""

    tab_labels = ["ユーザー一覧", "新規追加", "変更 / 削除"]
    selected_tab = st.radio("ユーザー管理タブ", tab_labels, index=st.session_state.get("user_admin_tab_index", 0), horizontal=True, label_visibility="collapsed")
    st.session_state["user_admin_tab_index"] = tab_labels.index(selected_tab)

    users = load_users()

    if selected_tab == "ユーザー一覧":
        rows = []
        for uid, info in users.items():
            rows.append({
                "ユーザーID": uid,
                "表示名": info.get("display_name", uid),
                "権限": info.get("role", "client"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    elif selected_tab == "新規追加":
        reset_counter = st.session_state.get("user_add_reset_counter", 0)
        uid_key = f"user_add_id_{reset_counter}"
        pw_key = f"user_add_pw_{reset_counter}"
        name_key = f"user_add_name_{reset_counter}"
        role_key = f"user_add_role_{reset_counter}"

        st.caption("追加ボタンを押すと、登録中の表示のあと、入力欄をクリアして一覧へ戻ります。")
        with st.form("add_user_form", clear_on_submit=False):
            new_id = st.text_input("新規ユーザーID（英数字 / _ / -）", key=uid_key)
            new_pw = st.text_input("新規パスワード", type="password", key=pw_key)
            new_display = st.text_input("表示名", key=name_key)
            new_role = st.selectbox("権限", ["client", "admin"], index=0, key=role_key)
            submitted = st.form_submit_button("ユーザー追加")

        if submitted:
            uid = new_id.strip()
            if uid == "":
                st.error("ユーザーIDを入力してください。")
            elif not valid_user_id(uid):
                st.error("ユーザーIDは英数字、_、- のみ使えます。")
            elif uid in users:
                st.error("そのユーザーIDは既に存在します。")
            elif new_pw.strip() == "":
                st.error("パスワードを入力してください。")
            else:
                with st.spinner("ユーザー登録中…"):
                    time.sleep(0.3)
                    users[uid] = {
                        "password": new_pw.strip(),
                        "role": new_role,
                        "display_name": new_display.strip() or uid,
                    }
                    save_users(users)

                st.session_state["user_add_success_message"] = f"ユーザー『{uid}』を登録できました。"
                st.session_state["user_add_reset_counter"] += 1
                st.session_state["user_admin_tab_index"] = 0
                st.rerun()

    elif selected_tab == "変更 / 削除":
        editable_users = sorted(users.keys())
        if editable_users:
            selected = st.selectbox("対象ユーザー", editable_users, key="admin_edit_user")
            info = users[selected]
            with st.form("edit_user_form"):
                edit_display = st.text_input("表示名", value=info.get("display_name", selected))
                edit_role = st.selectbox("権限", ["client", "admin"], index=0 if info.get("role", "client") == "client" else 1)
                edit_pw = st.text_input("新しいパスワード（変更しないなら空欄）", type="password")
                save_edit = st.form_submit_button("保存")
            if save_edit:
                users[selected]["display_name"] = edit_display.strip() or selected
                users[selected]["role"] = edit_role
                if edit_pw.strip():
                    users[selected]["password"] = edit_pw.strip()
                save_users(users)
                st.session_state["user_edit_success_message"] = f"ユーザー『{selected}』を編集できました。"
                st.rerun()

            dc1, dc2 = st.columns([1, 2])
            with dc1:
                if selected != st.session_state.get("user_id") and st.button("このユーザーを削除", key="delete_user_btn"):
                    with st.spinner("ユーザー削除中…"):
                        users.pop(selected, None)
                        save_users(users)
                        prefix = f"{selected}__"
                        for p in TEMPLATE_DIR.glob(f"{prefix}*.json"):
                            p.unlink(missing_ok=True)
                    st.success(f"ユーザー『{selected}』を削除できました。")
                    st.rerun()
            with dc2:
                if selected == st.session_state.get("user_id"):
                    st.caption("ログイン中の自分自身は削除できません。")

init_session()

# =========================================================
# Postgres保存 最終上書き
# ここより前に同名関数があっても、ここでDB対応版に上書きする
# =========================================================
def list_templates():
    db_templates = db_get("templates", None)
    if db_templates is not None:
        return sorted(list(db_templates.keys()))
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    return sorted([p.stem for p in templates_dir.glob("*.json")])

def load_template(name):
    db_templates = db_get("templates", None)
    if db_templates is not None:
        return db_templates.get(name)
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def save_template(name, config):
    db_templates = db_get("templates", None)
    if db_templates is not None or USE_POSTGRES:
        db_templates = db_templates or {}
        db_templates[name] = config
        if db_set("templates", db_templates):
            return
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_template(name):
    db_templates = db_get("templates", None)
    if db_templates is not None:
        db_templates.pop(name, None)
        db_set("templates", db_templates)
        return
    templates_dir = globals().get("TEMPLATES_DIR", Path(__file__).parent / "data" / "templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    if path.exists():
        path.unlink()

def load_rules():
    db_rules = db_get("rules", None)
    if db_rules is not None:
        return db_rules
    try:
        if RULES_FILE.exists():
            data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def save_rule_entry(name, payload):
    rules = load_rules()
    rules[name] = payload
    if db_set("rules", rules):
        return
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_rule_entry(name):
    rules = load_rules()
    rules.pop(name, None)
    if db_set("rules", rules):
        return
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

def load_ship_date_store(owner):
    owner = str(owner)
    key = f"ship_date_store::{owner}"
    db_val = db_get(key, None)
    if db_val is not None:
        return db_val
    path = ship_setting_path_for(owner)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default_ship_date_store()

def save_ship_date_store(arg1, arg2=None):
    if isinstance(arg1, dict):
        store = arg1
        owner = arg2
    else:
        owner = arg1
        store = arg2
    owner = str(owner)
    key = f"ship_date_store::{owner}"
    if db_set(key, store):
        return
    path = ship_setting_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

def load_picklist_mapping_store(owner):
    owner = str(owner)
    key = f"picklist_mapping_store::{owner}"
    db_val = db_get(key, None)
    if db_val is not None:
        return db_val
    path = picklist_mapping_path_for(owner)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default_picklist_mapping_store()

def save_picklist_mapping_store(arg1, arg2=None):
    if isinstance(arg1, dict):
        store = arg1
        owner = arg2
    else:
        owner = arg1
        store = arg2
    owner = str(owner)
    key = f"picklist_mapping_store::{owner}"
    if db_set(key, store):
        return
    path = picklist_mapping_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

def load_product_master_df(owner):
    owner = str(owner)
    key = f"product_master::{owner}"
    db_records = db_get(key, None)
    if db_records is not None:
        df = _records_to_df_for_db(db_records)
        if df is not None:
            return normalize_product_master_df(df)
    path = product_master_path_for(owner)
    if path.exists():
        try:
            return normalize_product_master_df(pd.read_csv(path, dtype=str).fillna(""))
        except Exception:
            pass
    return normalize_product_master_df(pd.DataFrame())

def save_product_master_df(arg1, arg2):
    if hasattr(arg1, "copy"):
        df = arg1
        owner = arg2
    else:
        owner = arg1
        df = arg2
    owner = str(owner)
    normalized = normalize_product_master_df(df)
    key = f"product_master::{owner}"
    records = _df_to_records_for_db(normalized)
    if db_set(key, records):
        return
    path = product_master_path_for(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(path, index=False, encoding="utf-8-sig")

def render_db_status():
    if USE_POSTGRES:
        st.caption("保存先: Render Postgres")
    else:
        st.caption("保存先: 一時ファイル（DATABASE_URL未設定）")


inject_custom_style()

st.markdown("""
<style>
/* =========================================================
   ログイン後：完全ライト化・見やすさ優先
   ========================================================= */

html, body, .stApp {
    background: linear-gradient(135deg,#ffffff 0%,#f8fbff 55%,#edf6ff 100%) !important;
    color: #0f172a !important;
}

/* Streamlitの濃紺背景を消す */
.main,
.block-container,
section.main,
[data-testid="stAppViewContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stHorizontalBlock"],
.element-container {
    background: transparent !important;
    color: #0f172a !important;
}

/* 上部ヘッダー */
[data-testid="stHeader"] {
    background: rgba(255,255,255,.96) !important;
    border-bottom: 1px solid #e2e8f0 !important;
    backdrop-filter: blur(12px) !important;
}

/* サイドバー */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}

/* 見出し・本文 */
h1, h2, h3, h4, h5, h6 {
    color: #0b2f78 !important;
    opacity: 1 !important;
}
p, span, label, div, small {
    opacity: 1 !important;
}

/* 上部ブランドバー */
.v2-topbar {
    background: #ffffff !important;
    border: 1px solid #dbeafe !important;
    border-radius: 26px !important;
    box-shadow: 0 12px 30px rgba(15,23,42,.055) !important;
    color: #0f172a !important;
}
.v2-topbar * {
    color: #0f172a !important;
}
.v2-brand-title {
    background: linear-gradient(135deg,#0b3a88 0%,#2563eb 55%,#22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.v2-brand-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}
.v2-user-pill {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}

/* ダッシュボードタイトル */
.v2-section-title {
    color: #0b3a88 !important;
    font-size: 38px !important;
    font-weight: 950 !important;
}

/* カード類 */
.v2-card,
.v2-quick-item,
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.05) !important;
    color: #0f172a !important;
}
.v2-card {
    border-radius: 24px !important;
}
.v2-card *,
.v2-quick-item *,
[data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.v2-card-label {
    color: #475569 !important;
    font-weight: 850 !important;
}
.v2-card-num {
    color: #0b3a88 !important;
    font-weight: 950 !important;
}
.v2-card-sub {
    color: #64748b !important;
}
.v2-quick-item {
    color: #0b3a88 !important;
    border-radius: 18px !important;
}
.v2-quick-item * {
    color: #0b3a88 !important;
}
.v2-quick-item:hover {
    background: #eff6ff !important;
}

/* 入力・選択欄 */
input,
textarea,
[data-baseweb="input"],
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
}
label,
[data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
    opacity: 1 !important;
}

/* ボタン */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg,#2563eb 0%,#22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 900 !important;
    box-shadow: 0 10px 24px rgba(37,99,235,.18) !important;
}
.stButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* secondary系ボタン */
button[kind="secondary"] {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}
button[kind="secondary"] * {
    color: #0b3a88 !important;
}

/* タブ・ラジオ */
[role="tab"],
[role="radiogroup"] label {
    color: #0f172a !important;
    opacity: 1 !important;
}

/* 濃紺・黒背景の残骸を白系へ */
[style*="background:#0"],
[style*="background: #0"],
[style*="background-color:#0"],
[style*="background-color: #0"],
[style*="rgb(2, 6, 23)"],
[style*="rgb(15, 23, 42)"] {
    background: #ffffff !important;
    color: #0f172a !important;
}

/* 白文字の残骸対策。ただしボタン内は白のまま */
[style*="color: white"],
[style*="color:#fff"],
[style*="color: #fff"],
[style*="color: rgb(255, 255, 255)"] {
    color: #0f172a !important;
}
.stButton [style*="color: white"],
.stButton [style*="color:#fff"],
.stButton [style*="color: #fff"],
.stButton [style*="color: rgb(255, 255, 255)"],
[data-testid="stFormSubmitButton"] [style*="color: white"],
[data-testid="stFormSubmitButton"] [style*="color:#fff"],
[data-testid="stFormSubmitButton"] [style*="color: #fff"],
[data-testid="stFormSubmitButton"] [style*="color: rgb(255, 255, 255)"] {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* =========================================================
   最終調整：ログイン画面寄せの白ベース＋Cloud雲マーク修正
   ========================================================= */

/* 全体をログイン画面に近い白〜薄水色に固定 */
.stApp {
    background:
        radial-gradient(circle at 16% 8%, rgba(255,255,255,1), transparent 34%),
        radial-gradient(circle at 86% 4%, rgba(255,255,255,1), transparent 38%),
        linear-gradient(135deg, #ffffff 0%, #f7fbff 58%, #e9f5ff 100%) !important;
    color: #0f172a !important;
}

/* 上の黒っぽいバーを消して白へ */
[data-testid="stHeader"] {
    background: rgba(255,255,255,.96) !important;
    border-bottom: 1px solid #e5edf7 !important;
    backdrop-filter: blur(14px) !important;
}

/* サイドバーも白ベース */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 70%, #eef6ff 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}

/* メイン本文の視認性 */
.block-container {
    max-width: 1280px !important;
    padding-top: 2.0rem !important;
    color: #0f172a !important;
}
h1, h2, h3, h4 {
    color: #0b2f78 !important;
    opacity: 1 !important;
}

/* 上部ブランドバー */
.v2-topbar {
    background: rgba(255,255,255,.94) !important;
    color: #0f172a !important;
    border: 1px solid #dbeafe !important;
    border-radius: 26px !important;
    box-shadow: 0 14px 36px rgba(37,99,235,.10) !important;
}
.v2-topbar * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 55%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.v2-brand-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}
.v2-user-pill {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}

/* カード類：白基調＋濃い文字 */
.v2-card,
.v2-quick-item,
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: rgba(255,255,255,.96) !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.055) !important;
}
.v2-card {
    border-radius: 24px !important;
}
.v2-card *,
.v2-quick-item *,
[data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.v2-card-label {
    color: #475569 !important;
    font-weight: 850 !important;
}
.v2-card-num,
.v2-section-title {
    color: #0b3a88 !important;
    font-weight: 950 !important;
}
.v2-card-sub {
    color: #64748b !important;
}
.v2-quick-item {
    border-radius: 18px !important;
}
.v2-quick-item,
.v2-quick-item * {
    color: #0b3a88 !important;
}
.v2-quick-item:hover {
    background: #eff6ff !important;
}

/* 入力欄・選択欄 */
[data-baseweb="input"],
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
textarea,
input {
    background: #ffffff !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}
label,
[data-testid="stMarkdownContainer"] p,
p, span {
    color: #334155;
    opacity: 1;
}

/* ボタンは青アクセント */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 900 !important;
    box-shadow: 0 10px 24px rgba(37,99,235,.18) !important;
}
.stButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* secondary系 */
button[kind="secondary"] {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}
button[kind="secondary"] * {
    color: #0b3a88 !important;
}

/* Cloudロゴ横の雲マーク：切れずに雲っぽく見える形へ */
.true-logo-main {
    padding-right: 74px !important;
    overflow: visible !important;
}
.true-logo-cloudmark {
    right: -64px !important;
    top: -20px !important;
    width: 86px !important;
    height: 56px !important;
    border: 0 !important;
    opacity: 1 !important;
    background: transparent !important;
}
.true-logo-cloudmark::before {
    content: "";
    position: absolute;
    left: 8px;
    top: 12px;
    width: 68px;
    height: 38px;
    border: 7px solid #28a9e6;
    border-bottom: none;
    border-radius: 42px 42px 0 0;
}
.true-logo-cloudmark::after {
    content: "";
    position: absolute;
    left: 2px;
    top: 28px;
    width: 82px;
    height: 24px;
    border-top: 7px solid #28a9e6;
    border-radius: 999px;
}

/* 古い白文字の残り対策 */
[style*="color: white"],
[style*="color:#fff"],
[style*="color: #fff"],
[style*="color: rgb(255, 255, 255)"] {
    color: #0f172a !important;
}
.stButton [style*="color: white"],
.stButton [style*="color:#fff"],
.stButton [style*="color: #fff"],
.stButton [style*="color: rgb(255, 255, 255)"] {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== 見やすさ優先：白基調ダッシュボード完全版 ===== */

.stApp {
    background: linear-gradient(135deg, #ffffff 0%, #f8fbff 62%, #eef6ff 100%) !important;
    color: #0f172a !important;
}
[data-testid="stHeader"] {
    background: rgba(255,255,255,.96) !important;
    border-bottom: 1px solid #e2e8f0 !important;
    backdrop-filter: blur(10px) !important;
}
.block-container {
    max-width: 1280px !important;
    padding-top: 2rem !important;
}

/* サイドバー */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}
[data-testid="stSidebar"] img {
    border-radius: 12px !important;
}

/* 見出し */
h1, h2, h3, h4 {
    color: #0b2f78 !important;
    opacity: 1 !important;
}

/* 上部ブランドバー */
.v2-topbar {
    background: #ffffff !important;
    border: 1px solid #dbeafe !important;
    border-radius: 24px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.06) !important;
    color: #0f172a !important;
}
.v2-topbar * {
    color: #0f172a !important;
}
.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 58%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size: 30px !important;
}
.v2-brand-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}
.v2-user-pill {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}

/* ダッシュボードタイトル */
.v2-section-title {
    color: #0b2f78 !important;
    font-size: 34px !important;
    font-weight: 950 !important;
}

/* KPIカード */
.v2-card {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 22px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.055) !important;
    min-height: 125px !important;
}
.v2-card *,
.v2-card-label,
.v2-card-num,
.v2-card-sub {
    opacity: 1 !important;
}
.v2-card-label {
    color: #475569 !important;
    font-weight: 850 !important;
}
.v2-card-num {
    color: #0b3a88 !important;
    font-weight: 950 !important;
}
.v2-card-sub {
    color: #64748b !important;
}

/* クイック操作 */
.v2-quick-item {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #dbeafe !important;
    border-radius: 18px !important;
    box-shadow: 0 8px 20px rgba(15,23,42,.04) !important;
}
.v2-quick-item * {
    color: #0b3a88 !important;
    opacity: 1 !important;
}
.v2-quick-item:hover {
    background: #eff6ff !important;
}

/* Expander・設定枠 */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 18px !important;
    box-shadow: 0 8px 22px rgba(15,23,42,.04) !important;
}
[data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.streamlit-expanderHeader {
    color: #0b2f78 !important;
    font-weight: 900 !important;
}

/* 入力欄・セレクト */
[data-baseweb="input"],
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
textarea {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    color: #0f172a !important;
}
input, textarea {
    background: #ffffff !important;
    color: #0f172a !important;
}
label,
[data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
    opacity: 1 !important;
}

/* ボタン */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 14px !important;
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 900 !important;
    box-shadow: 0 10px 22px rgba(37,99,235,.18) !important;
}
.stButton > button p,
[data-testid="stFormSubmitButton"] button p,
.stButton > button span,
[data-testid="stFormSubmitButton"] button span {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* secondary系 */
button[kind="secondary"] {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}
button[kind="secondary"] p,
button[kind="secondary"] span {
    color: #0b3a88 !important;
}

/* 表 */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #ffffff !important;
    border-radius: 18px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 8px 22px rgba(15,23,42,.045) !important;
}

/* アラート */
[data-testid="stAlert"] {
    border-radius: 16px !important;
    border: 1px solid #e2e8f0 !important;
}

/* タブ・ラジオ */
[role="tab"],
[role="radiogroup"] label {
    color: #0f172a !important;
    opacity: 1 !important;
}

/* サイドバー下部説明 */
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p {
    color: #475569 !important;
}

/* 薄すぎる白文字を強制補正 */
[style*="color: white"],
[style*="color:#fff"],
[style*="color: #fff"],
[style*="color: rgb(255, 255, 255)"] {
    color: #0f172a !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* =========================================================
   出荷ラクっと Cloud：Apple風ライトダッシュボード完全版
   ========================================================= */

.stApp {
    background:
        radial-gradient(circle at 18% 6%, rgba(219,234,254,.55), transparent 34%),
        radial-gradient(circle at 86% 10%, rgba(224,242,254,.45), transparent 30%),
        linear-gradient(135deg, #ffffff 0%, #fbfdff 52%, #eef7ff 100%) !important;
    color: #0f172a !important;
}

[data-testid="stHeader"] {
    background: rgba(255,255,255,.82) !important;
    backdrop-filter: blur(18px) saturate(160%) !important;
    border-bottom: 1px solid rgba(226,232,240,.7) !important;
}

.block-container {
    max-width: 1240px !important;
    padding-top: 2.2rem !important;
}

[data-testid="stSidebar"] {
    background: rgba(255,255,255,.86) !important;
    backdrop-filter: blur(22px) saturate(170%) !important;
    border-right: 1px solid rgba(226,232,240,.9) !important;
}
[data-testid="stSidebar"] * {
    color: #0f2f66 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}
[data-testid="stSidebar"] img {
    border-radius: 18px !important;
    box-shadow: 0 12px 28px rgba(37,99,235,.12) !important;
}

h1, h2, h3 {
    color: #0b2f78 !important;
    letter-spacing: -.02em !important;
}
h1 { font-weight: 950 !important; }
h2 { font-weight: 900 !important; }

.v2-topbar {
    background: rgba(255,255,255,.80) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    color: #0b2f78 !important;
    border: 1px solid rgba(203,213,225,.72) !important;
    box-shadow:
        0 18px 50px rgba(15,23,42,.07),
        inset 0 1px 0 rgba(255,255,255,.75) !important;
    border-radius: 28px !important;
}
.v2-topbar * { color: #0b2f78 !important; }
.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 55%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size: 30px !important;
    letter-spacing: -.03em !important;
}
.v2-brand-sub { color: #64748b !important; }
.v2-user-pill {
    background: rgba(239,246,255,.88) !important;
    color: #0b3a88 !important;
    border: 1px solid rgba(191,219,254,.9) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.9) !important;
}

.v2-section-title {
    color: #0b2f78 !important;
    font-size: 34px !important;
    font-weight: 950 !important;
    letter-spacing: -.04em !important;
    margin-top: 26px !important;
}

.v2-card {
    background: rgba(255,255,255,.86) !important;
    backdrop-filter: blur(18px) saturate(170%) !important;
    border: 1px solid rgba(226,232,240,.92) !important;
    box-shadow:
        0 18px 42px rgba(15,23,42,.06),
        inset 0 1px 0 rgba(255,255,255,.85) !important;
    border-radius: 26px !important;
    min-height: 132px !important;
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
}
.v2-card:hover {
    transform: translateY(-3px) !important;
    box-shadow:
        0 24px 54px rgba(37,99,235,.11),
        inset 0 1px 0 rgba(255,255,255,.9) !important;
    border-color: rgba(191,219,254,.95) !important;
}
.v2-card-label {
    color: #64748b !important;
    font-weight: 850 !important;
    letter-spacing: .02em !important;
}
.v2-card-num {
    color: #0b3a88 !important;
    font-weight: 950 !important;
    letter-spacing: -.04em !important;
}
.v2-card-sub { color: #94a3b8 !important; }

.v2-quick { gap: 14px !important; }
.v2-quick-item {
    background: rgba(255,255,255,.80) !important;
    backdrop-filter: blur(16px) saturate(170%) !important;
    border: 1px solid rgba(226,232,240,.92) !important;
    color: #0b3a88 !important;
    border-radius: 22px !important;
    box-shadow: 0 12px 30px rgba(15,23,42,.05) !important;
    transition: all .18s ease !important;
}
.v2-quick-item:hover {
    transform: translateY(-2px) !important;
    background: rgba(239,246,255,.92) !important;
    border-color: rgba(147,197,253,.95) !important;
    box-shadow: 0 18px 40px rgba(37,99,235,.11) !important;
}

[data-testid="stExpander"] {
    background: rgba(255,255,255,.76) !important;
    backdrop-filter: blur(16px) saturate(160%) !important;
    border: 1px solid rgba(226,232,240,.9) !important;
    border-radius: 20px !important;
    box-shadow: 0 12px 32px rgba(15,23,42,.045) !important;
}
.streamlit-expanderHeader {
    color: #0b2f78 !important;
    font-weight: 900 !important;
}

[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
[data-baseweb="select"],
[data-baseweb="input"],
textarea {
    background: rgba(255,255,255,.94) !important;
    border: 1px solid rgba(203,213,225,.95) !important;
    border-radius: 16px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.8) !important;
}
input, textarea { color: #0f172a !important; }
label, [data-testid="stMarkdownContainer"] p { color: #334155 !important; }

.stButton > button,
[data-testid="stFormSubmitButton"] button,
button[kind="primary"] {
    border-radius: 16px !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 12px 28px rgba(37,99,235,.22) !important;
    transition: all .16s ease !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover,
button[kind="primary"]:hover {
    filter: brightness(1.04) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 16px 34px rgba(37,99,235,.28) !important;
}
.stButton > button p,
[data-testid="stFormSubmitButton"] button p { color: #ffffff !important; }

button[kind="secondary"] {
    background: rgba(255,255,255,.86) !important;
    color: #0b3a88 !important;
    border: 1px solid rgba(191,219,254,.9) !important;
    box-shadow: 0 10px 24px rgba(15,23,42,.05) !important;
}
button[kind="secondary"] p { color: #0b3a88 !important; }

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: rgba(255,255,255,.88) !important;
    border-radius: 22px !important;
    border: 1px solid rgba(226,232,240,.92) !important;
    box-shadow: 0 16px 40px rgba(15,23,42,.055) !important;
    overflow: hidden !important;
}

[data-testid="stAlert"] {
    border-radius: 18px !important;
    border: 1px solid rgba(226,232,240,.9) !important;
    box-shadow: 0 12px 28px rgba(15,23,42,.045) !important;
}

[role="tab"] {
    color: #0b2f78 !important;
    font-weight: 850 !important;
}
[role="radiogroup"] label { color: #334155 !important; }

.caption, .stCaption, small { color: #64748b !important; }

[data-testid="stSidebar"] .stMarkdown { color: #475569 !important; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb {
    background: rgba(148,163,184,.42);
    border-radius: 999px;
}
::-webkit-scrollbar-track { background: transparent; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== ログイン後画面も白〜水色トーンへ統一 ===== */

/* 全体背景 */
.stApp {
    background:
        radial-gradient(circle at 15% 8%, rgba(255,255,255,1), transparent 34%),
        radial-gradient(circle at 84% 4%, rgba(255,255,255,1), transparent 38%),
        linear-gradient(135deg, #ffffff 0%, #f6fbff 45%, #e5f1ff 100%) !important;
    color: #0f172a !important;
}

/* 上の黒帯を白系に */
[data-testid="stHeader"] {
    background: rgba(255,255,255,.78) !important;
    backdrop-filter: blur(12px) !important;
}

/* サイドバー */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f3f8ff 55%, #e8f3ff 100%) !important;
    border-right: 1px solid rgba(191,219,254,.85) !important;
}
[data-testid="stSidebar"] * {
    color: #0f2f66 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}
[data-testid="stSidebar"] img {
    border-radius: 14px !important;
    box-shadow: 0 8px 24px rgba(37,99,235,.12) !important;
}

/* メインの見出し */
h1, h2, h3 {
    color: #0b2f78 !important;
}

/* ログイン後の上部ブランドバー */
.v2-topbar {
    background: rgba(255,255,255,.90) !important;
    color: #0b2f78 !important;
    border: 1px solid rgba(191,219,254,.88) !important;
    box-shadow: 0 18px 50px rgba(37,99,235,.13) !important;
}
.v2-topbar * {
    color: #0b2f78 !important;
}
.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 55%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.v2-brand-sub {
    color: #64748b !important;
}
.v2-user-pill {
    background: linear-gradient(135deg, #dbeafe, #eef6ff) !important;
    color: #0b3a88 !important;
    border: 1px solid rgba(191,219,254,.9) !important;
}

/* ダッシュボードカード */
.v2-card {
    background: rgba(255,255,255,.92) !important;
    border: 1px solid rgba(203,213,225,.82) !important;
    box-shadow: 0 18px 48px rgba(37,99,235,.12) !important;
}
.v2-card-label {
    color: #475569 !important;
}
.v2-card-num {
    color: #0b3a88 !important;
}
.v2-card-sub {
    color: #64748b !important;
}

/* クイック操作 */
.v2-quick-item {
    background: rgba(255,255,255,.82) !important;
    border: 1px solid rgba(191,219,254,.88) !important;
    color: #0b3a88 !important;
    box-shadow: 0 10px 30px rgba(37,99,235,.09) !important;
}
.v2-quick-item:hover {
    background: #eff6ff !important;
}

/* 入力欄・セレクト */
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
textarea,
input {
    background: rgba(255,255,255,.95) !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}
label, p, span, div {
    /* 全部を強制しすぎないよう、本文系だけ濃くする */
}

/* expander / 設定ボックス */
.streamlit-expanderHeader,
[data-testid="stExpander"] {
    background: rgba(255,255,255,.80) !important;
    border-color: rgba(191,219,254,.75) !important;
    color: #0b2f78 !important;
}
[data-testid="stExpander"] * {
    color: #0f172a;
}

/* テーブル */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: rgba(255,255,255,.92) !important;
    border-radius: 18px !important;
    box-shadow: 0 14px 38px rgba(37,99,235,.10) !important;
}

/* ボタン */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 14px !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 12px 28px rgba(37,99,235,.20) !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    filter: brightness(1.04) !important;
    transform: translateY(-1px) !important;
}

/* アラート */
[data-testid="stAlert"] {
    border-radius: 16px !important;
}

/* テンプレート選択周辺 */
.block-container {
    color: #0f172a !important;
}

/* 既存の濃紺文字を白背景でも読めるように */
.caption, .stCaption {
    color: #64748b !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== 微調整：壁なじませ・雲マーク修正・年号修正 ===== */

/* 右の壁を真っ白ではなく、背景になじむ薄い水色グラデに */
.true-peek-wall {
    background:
        linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(242,248,255,.96) 52%, rgba(226,241,255,.96) 100%) !important;
    border-left: 1px solid rgba(191,219,254,.85) !important;
    box-shadow:
        -18px 0 42px rgba(37,99,235,.10),
        inset 14px 0 26px rgba(219,234,254,.42) !important;
}

/* 壁の境界を少し柔らかく */
.true-peek-wrap::before {
    content: "";
    position: absolute;
    right: 112px;
    top: 0;
    width: 42px;
    height: 100vh;
    background: linear-gradient(90deg, rgba(219,234,254,0), rgba(219,234,254,.28));
    z-index: 4;
    pointer-events: none;
}

/* Cloudの雲マークが切れないようにロゴ周辺の余白を確保 */
.true-logo-main {
    padding-right: 42px !important;
    overflow: visible !important;
}
.true-logo-cloudmark {
    right: -46px !important;
    top: -20px !important;
    width: 76px !important;
    height: 50px !important;
    border-width: 6px !important;
}

/* フッター年号：サービス開始想定に合わせて2026へ */
.block-container::after {
    content: "© 2026 出荷ラクっと Cloud. All rights reserved." !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== 最終寄せ：カード大きく・右壁を画面端まで・キャラ大きく ===== */

/* ロゴとカードの間隔を2枚目に近づける */
.true-brand {
    margin-top: 30px !important;
    margin-bottom: 28px !important;
}
.true-logo-jp {
    font-size: 72px !important;
}
.true-logo-cloud {
    font-size: 58px !important;
}

/* ログインカード全体を大きく */
[data-testid="stHorizontalBlock"] {
    max-width: 1500px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
.mock-login-card-head {
    padding: 42px 58px 12px 58px !important;
    border-radius: 32px 32px 0 0 !important;
}
.mock-lock {
    width: 56px !important;
    height: 56px !important;
    font-size: 26px !important;
    margin-bottom: 10px !important;
}
.mock-login-title {
    font-size: 36px !important;
    margin-bottom: 16px !important;
}
.mock-login-desc {
    font-size: 17px !important;
    margin-bottom: 30px !important;
}
[data-testid="stForm"] {
    padding: 0 58px 44px 58px !important;
    border-radius: 0 0 32px 32px !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p {
    font-size: 16px !important;
}
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    border-radius: 16px !important;
}
[data-testid="stForm"] input {
    min-height: 64px !important;
    font-size: 17px !important;
}
[data-testid="stFormSubmitButton"] button {
    min-height: 70px !important;
    border-radius: 20px !important;
    font-size: 22px !important;
    margin-top: 28px !important;
}

/* 右の壁：画面を縦に切る感じで固定 */
.true-peek-wrap {
    position: fixed !important;
    right: 0 !important;
    top: 0 !important;
    width: 360px !important;
    height: 100vh !important;
    z-index: 8 !important;
    pointer-events: none !important;
}
.true-peek-wall {
    position: absolute !important;
    right: 0 !important;
    top: 0 !important;
    width: 150px !important;
    height: 100vh !important;
    background: #ffffff !important;
    border-left: 1px solid #dbeafe !important;
    border-radius: 0 !important;
    box-shadow: -20px 0 45px rgba(37,99,235,.10) !important;
    z-index: 3 !important;
}

/* キャラを大きく、壁の後ろからしっかり覗かせる */
.true-peek-character {
    position: absolute !important;
    right: 78px !important;
    top: 31vh !important;
    width: 280px !important;
    z-index: 2 !important;
    filter: drop-shadow(0 24px 42px rgba(15,23,42,.22)) !important;
    animation: truePeekBig 5.5s ease-in-out infinite !important;
}
@keyframes truePeekBig {
    0%, 18% {
        transform: translateX(96px) rotate(-3deg);
        opacity: .72;
    }
    42%, 66% {
        transform: translateX(0) rotate(-1deg);
        opacity: 1;
    }
    86%, 100% {
        transform: translateX(96px) rotate(-3deg);
        opacity: .72;
    }
}

/* フッター位置 */
.block-container::after {
    margin-top: 34px !important;
}

@media (max-width: 1200px) {
    .true-peek-character {
        width: 220px !important;
        right: 70px !important;
    }
    .true-peek-wall {
        width: 120px !important;
    }
}
@media (max-width: 980px) {
    .true-logo-jp { font-size: 44px !important; }
    .true-logo-cloud { font-size: 36px !important; }
    .true-peek-wrap { display: none !important; }
    .mock-login-card-head { padding: 32px 28px 10px 28px !important; }
    [data-testid="stForm"] { padding: 0 28px 34px 28px !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== 添付イメージ寄せ 最終調整 ===== */

/* 全体を明るい白〜水色に固定 */
html, body, .stApp {
    background:
        radial-gradient(circle at 18% 16%, rgba(230,242,255,.95), transparent 34%),
        radial-gradient(circle at 80% 10%, rgba(255,255,255,1), transparent 38%),
        linear-gradient(135deg, #ffffff 0%, #f5faff 42%, #e6f1ff 100%) !important;
    color: #0f172a !important;
}

/* 以前の濃紺背景・ぼかしレイヤーを無効化 */
.stApp::before,
.login-bg-blur,
.peek-robot {
    display: none !important;
}

/* 画面下の淡い波 */
.mock-login-page::before {
    content: "";
    position: fixed;
    inset: auto 0 0 0;
    height: 35vh;
    background:
      radial-gradient(ellipse at 22% 95%, rgba(191,219,254,.52), transparent 56%),
      radial-gradient(ellipse at 74% 84%, rgba(224,242,254,.88), transparent 56%);
    opacity: .95;
    z-index: 0;
    pointer-events: none;
}

/* ロゴを明るく・大きく */
.mock-brand {
    margin-top: 30px !important;
    margin-bottom: 22px !important;
    text-align: center !important;
    position: relative !important;
    z-index: 3 !important;
}
.mock-logo-jp {
    font-size: 66px !important;
    font-weight: 950 !important;
    background: linear-gradient(135deg, #082c73 0%, #155ee6 58%, #20b8e8 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    filter: drop-shadow(0 10px 22px rgba(37,99,235,.14)) !important;
}
.mock-logo-cloud {
    font-size: 52px !important;
    font-weight: 900 !important;
    font-style: italic !important;
    background: linear-gradient(135deg, #2563eb, #21b8e8) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.mock-subtitle {
    color: #64748b !important;
    font-weight: 850 !important;
}

/* 右から覗くロボ：base64表示、右端から自然に */
.mock-peek-robot {
    position: fixed !important;
    right: -18px !important;
    top: 38% !important;
    width: 255px !important;
    max-width: 20vw !important;
    z-index: 2 !important;
    display: block !important;
    opacity: 1 !important;
    filter: drop-shadow(0 18px 34px rgba(15,23,42,.18)) !important;
    animation: mockPeekFinal 5.8s ease-in-out infinite !important;
    pointer-events: none !important;
}
@keyframes mockPeekFinal {
    0%, 18% { transform: translateX(54px) rotate(-2deg); opacity: .72; }
    42%, 66% { transform: translateX(0) rotate(-1deg); opacity: 1; }
    86%, 100% { transform: translateX(54px) rotate(-2deg); opacity: .72; }
}

/* ログインカード */
.mock-login-card-head {
    background: rgba(255,255,255,.90) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(203,213,225,.72) !important;
    border-bottom: none !important;
    border-radius: 28px 28px 0 0 !important;
    padding: 34px 48px 8px 48px !important;
    box-shadow: 0 20px 60px rgba(59,130,246,.14) !important;
    text-align: center !important;
}
.mock-login-card-head *,
.mock-login-title,
.mock-login-desc {
    opacity: 1 !important;
}
.mock-login-title {
    color: #0b2f78 !important;
    font-size: 30px !important;
    font-weight: 950 !important;
}
.mock-login-desc {
    color: #64748b !important;
    font-weight: 800 !important;
}

/* フォームも同じ1枚カードに見せる */
[data-testid="stForm"] {
    background: rgba(255,255,255,.90) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(203,213,225,.72) !important;
    border-top: none !important;
    border-radius: 0 0 28px 28px !important;
    padding: 0 48px 34px 48px !important;
    box-shadow: 0 24px 60px rgba(59,130,246,.13) !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p {
    color: #0b2f78 !important;
    opacity: 1 !important;
    font-weight: 900 !important;
}
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    background: rgba(255,255,255,.96) !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 13px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
[data-testid="stForm"] [data-baseweb="input"] > div {
    background: transparent !important;
}
[data-testid="stForm"] input {
    background: transparent !important;
    color: #0f172a !important;
    border: none !important;
    min-height: 54px !important;
}
[data-testid="stForm"] input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
[data-testid="stForm"] button[kind="icon"],
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #64748b !important;
    width: auto !important;
    min-height: auto !important;
    margin: 0 !important;
}
[data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    min-height: 62px !important;
    margin-top: 22px !important;
    border-radius: 18px !important;
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 18px !important;
    font-weight: 950 !important;
    box-shadow: 0 16px 32px rgba(37,99,235,.28) !important;
}
[data-testid="stFormSubmitButton"] button p,
[data-testid="stFormSubmitButton"] button span {
    color: #ffffff !important;
    opacity: 1 !important;
}

/* 消した下部カードが残る場合も非表示 */
.mock-login-footer,
.mock-divider,
.mock-sso {
    display: none !important;
}

/* フッター */
.block-container::after {
    content: "© 2026 出荷ラクっと Cloud. All rights reserved.";
    display: block;
    text-align: center;
    color: #94a3b8;
    font-weight: 700;
    margin: 28px 0 8px 0;
}

@media (max-width: 980px) {
    .mock-logo-jp { font-size: 42px !important; }
    .mock-logo-cloud { font-size: 34px !important; }
    .mock-peek-robot { display: none !important; }
    .mock-logo-cloudmark,
    .mock-logo-main::after { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== Mockup style login screen ===== */
.stApp {
    background:
        radial-gradient(circle at 20% 20%, rgba(219,234,254,.85), transparent 32%),
        radial-gradient(circle at 82% 10%, rgba(255,255,255,.9), transparent 35%),
        linear-gradient(135deg, #f8fbff 0%, #eef6ff 46%, #dfeeff 100%) !important;
}
.stApp::before,
.login-bg-blur,
.peek-robot {
    display: none !important;
}
.block-container {
    padding-top: 1.5rem !important;
    max-width: 1500px !important;
}

/* background soft waves */
.mock-login-page::before {
    content: "";
    position: fixed;
    inset: auto 0 0 0;
    height: 34vh;
    background:
        radial-gradient(ellipse at 20% 90%, rgba(191,219,254,.55), transparent 55%),
        radial-gradient(ellipse at 78% 80%, rgba(224,242,254,.7), transparent 54%);
    opacity: .95;
    z-index: 0;
    pointer-events: none;
}
.mock-login-page {
    position: relative;
    z-index: 1;
}

/* Logo */
.mock-brand {
    text-align: center;
    margin-top: 28px;
    margin-bottom: 24px;
    position: relative;
    z-index: 3;
}
.mock-logo-main {
    display: inline-flex;
    align-items: baseline;
    gap: 16px;
    position: relative;
}
.mock-logo-jp {
    font-size: 68px;
    font-weight: 950;
    letter-spacing: .03em;
    line-height: 1;
    background: linear-gradient(135deg, #0b2f78 0%, #145de2 55%, #19b8df 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 10px 22px rgba(37,99,235,.16));
}
.mock-logo-cloud {
    font-size: 54px;
    font-weight: 900;
    font-style: italic;
    line-height: 1;
    background: linear-gradient(135deg, #2463df 0%, #29b7e6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.mock-logo-main::after {
    content: "✦";
    position: absolute;
    right: 185px;
    top: -28px;
    color: #22b6e9;
    font-size: 28px;
}
.mock-logo-cloudmark {
    position: absolute;
    right: -74px;
    top: -18px;
    width: 88px;
    height: 52px;
    border: 7px solid #28a9e6;
    border-bottom-color: transparent;
    border-radius: 50px 50px 18px 18px;
    opacity: .9;
}
.mock-logo-swoosh {
    width: 390px;
    height: 9px;
    margin: 12px auto 0 auto;
    background: linear-gradient(90deg, #1d4ed8, #22d3ee);
    clip-path: polygon(0 55%, 100% 0, 92% 45%, 10% 100%);
    opacity: .9;
}
.mock-subtitle {
    margin-top: 20px;
    color: #64748b;
    font-weight: 850;
    letter-spacing: .08em;
    font-size: 16px;
}

/* Peeking robot */
.mock-peek-robot {
    position: fixed;
    right: -6px;
    top: 37%;
    width: 270px;
    max-width: 20vw;
    z-index: 2;
    filter: drop-shadow(0 18px 34px rgba(15,23,42,.18));
    animation: mockPeek 5.5s ease-in-out infinite;
    pointer-events: none;
}
@keyframes mockPeek {
    0%, 18% { transform: translateX(52px) rotate(-2deg); opacity: .72; }
    42%, 66% { transform: translateX(0) rotate(-1deg); opacity: 1; }
    86%, 100% { transform: translateX(52px) rotate(-2deg); opacity: .72; }
}

/* Login card */
.mock-login-card-head {
    background: rgba(255,255,255,.86);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(203,213,225,.76);
    border-bottom: none;
    border-radius: 28px 28px 0 0;
    padding: 34px 48px 8px 48px;
    box-shadow: 0 20px 60px rgba(59,130,246,.14);
    text-align: center;
}
.mock-lock {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    color: #2563eb;
    background: linear-gradient(135deg, #dbeafe, #eef6ff);
    font-size: 22px;
    font-weight: 900;
    margin-bottom: 8px;
}
.mock-login-title {
    color: #0b2f78;
    font-size: 30px;
    font-weight: 950;
    margin-bottom: 12px;
}
.mock-login-desc {
    color: #64748b;
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 24px;
}
[data-testid="stForm"] {
    background: rgba(255,255,255,.86) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(203,213,225,.76) !important;
    border-top: none !important;
    border-radius: 0 0 28px 28px !important;
    padding: 0 48px 28px 48px !important;
    box-shadow: 0 20px 60px rgba(59,130,246,.14) !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p {
    color: #0b2f78 !important;
    opacity: 1 !important;
    font-weight: 900 !important;
}
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    background: rgba(255,255,255,.92) !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 13px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
[data-testid="stForm"] input {
    background: transparent !important;
    color: #0f172a !important;
    border: none !important;
    min-height: 54px !important;
    caret-color: #0f172a !important;
}
[data-testid="stForm"] input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
[data-testid="stForm"] button[kind="icon"],
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #64748b !important;
    width: auto !important;
    min-height: auto !important;
    margin: 0 !important;
}
[data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    min-height: 62px !important;
    margin-top: 22px !important;
    border-radius: 18px !important;
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 18px !important;
    font-weight: 950 !important;
    box-shadow: 0 16px 32px rgba(37,99,235,.28) !important;
}
[data-testid="stFormSubmitButton"] button p,
[data-testid="stFormSubmitButton"] button span {
    color: #ffffff !important;
    opacity: 1 !important;
    font-weight: 950 !important;
}
.mock-login-footer {
    background: rgba(255,255,255,.86);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(203,213,225,.76);
    border-top: none;
    border-radius: 0 0 28px 28px;
    padding: 0 48px 34px 48px;
    text-align: center;
    margin-top: -28px;
    box-shadow: 0 24px 60px rgba(59,130,246,.12);
}
.mock-divider {
    display: flex;
    align-items: center;
    gap: 14px;
    color: #94a3b8;
    font-weight: 800;
    font-style: normal;
    margin: 18px 0;
}
.mock-divider span {
    flex: 1;
    height: 1px;
    background: #dbe3ef;
}
.mock-sso {
    color: #2563eb;
    font-weight: 950;
    font-size: 16px;
}

/* Loading */
@keyframes runAcross {
    0% { transform: translateX(-60px); opacity: 0; }
    15% { opacity: 1; }
    55% { transform: translateX(240px); opacity: 1; }
    100% { transform: translateX(520px); opacity: 0; }
}
@keyframes loadBar {
    0% { transform: translateX(-110%); }
    100% { transform: translateX(250%); }
}
.mock-loading {
    max-width: 480px;
    margin: 34px auto;
    background: rgba(255,255,255,.92);
    backdrop-filter: blur(12px);
    border-radius: 26px;
    padding: 26px;
    box-shadow: 0 24px 60px rgba(59,130,246,.16);
}
.mock-loading-robot {
    font-size: 36px;
    animation: runAcross 1.25s infinite linear;
}
.mock-loading-title {
    color: #0b2f78;
    font-size: 22px;
    font-weight: 950;
    margin-top: 12px;
}
.mock-loading-sub {
    color: #64748b;
    font-weight: 800;
    margin-top: 6px;
}
.mock-loading-bar {
    margin-top: 18px;
    height: 10px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
}
.mock-loading-bar span {
    display: block;
    height: 100%;
    width: 42%;
    background: linear-gradient(90deg, #2563eb, #22d3ee);
    border-radius: 999px;
    animation: loadBar 1s infinite ease-in-out;
}

/* Footer */
.block-container::after {
    content: "© 2026 出荷ラクっと Cloud. All rights reserved.";
    display: block;
    text-align: center;
    color: #94a3b8;
    font-weight: 700;
    margin: 28px 0 8px 0;
}

/* Mobile */
@media (max-width: 980px) {
    .mock-logo-jp { font-size: 42px; }
    .mock-logo-cloud { font-size: 34px; }
    .mock-logo-cloudmark { display: none; }
    .mock-logo-main::after { display: none; }
    .mock-logo-swoosh { width: 260px; }
    .mock-subtitle { font-size: 13px; }
    .mock-peek-robot { display: none; }
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    [data-testid="stForm"], .mock-login-card-head, .mock-login-footer {
        padding-left: 28px !important;
        padding-right: 28px !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== ログイン画面：安定した横並び完成版 ===== */

/* 背景画像・ぼかしは使わず、濃紺グラデーションに戻す */
.stApp {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 55%, #eef6ff 100%) !important;
}
.stApp::before,
.login-bg-blur {
    display: none !important;
}

/* 横並びエリアを広めに */
[data-testid="stHorizontalBlock"] {
    max-width: 1320px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* 左画像 */
[data-testid="stHorizontalBlock"] img {
    border-radius: 20px !important;
    box-shadow: 0 22px 56px rgba(2, 8, 23, .26) !important;
}

/* 上部ロゴ */
.login-final-title {
    max-width: 1320px !important;
    margin: 34px auto 20px auto !important;
    color: #ffffff !important;
    font-size: 34px !important;
    font-weight: 950 !important;
    letter-spacing: .02em !important;
}

/* 右ログインカード */
.login-side-head {
    background: #ffffff !important;
    color: #0f172a !important;
    border-radius: 28px 28px 0 0 !important;
    padding: 46px 50px 10px 50px !important;
    border: 1px solid #e2e8f0 !important;
    border-bottom: none !important;
    box-shadow: 0 22px 56px rgba(2,8,23,.18) !important;
}
.login-side-head * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.login-side-logo {
    color: #0b3a88 !important;
    font-size: 28px !important;
    font-weight: 950 !important;
    margin-bottom: 52px !important;
}
.login-side-title {
    color: #0f172a !important;
    font-size: 34px !important;
    font-weight: 950 !important;
    margin-bottom: 12px !important;
}
.login-side-desc {
    color: #475569 !important;
    font-size: 16px !important;
    font-weight: 750 !important;
    margin-bottom: 22px !important;
}

/* フォームを白く統一 */
[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 28px 28px !important;
    padding: 0 50px 50px 50px !important;
    box-shadow: 0 22px 56px rgba(2,8,23,.18) !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p {
    color: #334155 !important;
    opacity: 1 !important;
    font-weight: 850 !important;
}
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
[data-testid="stForm"] [data-baseweb="input"] > div {
    background: #ffffff !important;
}
[data-testid="stForm"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    border: none !important;
    min-height: 56px !important;
    caret-color: #0f172a !important;
}
[data-testid="stForm"] input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
[data-testid="stForm"] button[kind="icon"],
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #334155 !important;
    width: auto !important;
    min-height: auto !important;
    margin: 0 !important;
}

/* ログインボタン */
[data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    min-height: 58px !important;
    margin-top: 18px !important;
    border-radius: 14px !important;
    background: linear-gradient(135deg,#1464e8,#0b55d9) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 18px !important;
    font-weight: 950 !important;
    box-shadow: 0 14px 30px rgba(37,99,235,.25) !important;
}
[data-testid="stFormSubmitButton"] button p,
[data-testid="stFormSubmitButton"] button span {
    color: #ffffff !important;
    opacity: 1 !important;
    font-weight: 950 !important;
}

/* ローディングはシンプルで見やすく */
@keyframes simpleBarMove {
    0% { transform: translateX(-110%); }
    100% { transform: translateX(260%); }
}
.run-loader {
    max-width: 520px !important;
    margin: 32px auto !important;
    background: #ffffff !important;
    border-radius: 26px !important;
    padding: 28px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 28px 80px rgba(2,8,23,.28) !important;
    color: #0f172a !important;
}
.run-track {
    display: none !important;
}
.run-title {
    margin-top: 0 !important;
    font-size: 22px !important;
    font-weight: 950 !important;
    color: #0b3a88 !important;
}
.run-sub {
    margin-top: 8px !important;
    color: #334155 !important;
    font-weight: 800 !important;
}
.run-bar {
    margin-top: 18px !important;
    height: 12px !important;
    background: #e2e8f0 !important;
    border-radius: 999px !important;
    overflow: hidden !important;
    position: relative !important;
}
.run-bar span {
    position: absolute !important;
    inset: 0 !important;
    width: 45% !important;
    background: linear-gradient(90deg,#2563eb,#22d3ee) !important;
    border-radius: 999px !important;
    animation: simpleBarMove 1s infinite ease-in-out !important;
}

@media (max-width: 900px) {
    .login-final-title { font-size: 28px !important; margin-top: 24px !important; }
    .login-side-head { padding: 32px 28px 8px 28px !important; }
    [data-testid="stForm"] { padding: 0 28px 32px 28px !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.login-final-title {
    gap: 0 !important;
    letter-spacing: .02em !important;
}
.login-side-logo {
    color: #0b3a88 !important;
    font-size: 26px !important;
    font-weight: 950 !important;
    letter-spacing: .02em !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== PW欄・ログインボタン最終修正 ===== */

/* password reveal icon の黒背景・青かぶり対策 */
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

[data-testid="stForm"] [data-baseweb="input"] > div {
    background: #ffffff !important;
}

[data-testid="stForm"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    border: none !important;
    box-shadow: none !important;
}

/* 目アイコン側の余計な濃色背景を消す */
[data-testid="stForm"] button[kind="icon"],
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #334155 !important;
    min-height: auto !important;
    width: auto !important;
    margin: 0 !important;
}

/* ログインボタン文字を白で固定 */
[data-testid="stFormSubmitButton"] button,
[data-testid="stForm"] button[type="submit"] {
    background: linear-gradient(135deg,#1464e8,#0b55d9) !important;
    color: #ffffff !important;
    font-weight: 950 !important;
    opacity: 1 !important;
}

[data-testid="stFormSubmitButton"] button p,
[data-testid="stFormSubmitButton"] button span,
[data-testid="stForm"] button[type="submit"] p,
[data-testid="stForm"] button[type="submit"] span {
    color: #ffffff !important;
    opacity: 1 !important;
    font-weight: 950 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== ログイン見やすさ最終調整 ===== */
.login-side-head,
.login-side-head * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.login-side-logo {
    color: #0b3a88 !important;
}
.login-side-title {
    color: #0f172a !important;
}
.login-side-desc {
    color: #475569 !important;
}
.login-side-head {
    padding: 38px 46px 4px 46px !important;
}

/* フォーム内の文字色・ラベル・入力欄 */
[data-testid="stForm"],
[data-testid="stForm"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] p {
    color: #334155 !important;
    opacity: 1 !important;
}
[data-testid="stForm"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    caret-color: #0f172a !important;
}
[data-testid="stForm"] input::placeholder {
    color: #94a3b8 !important;
    opacity: 1 !important;
}
[data-testid="stForm"] button {
    color: #ffffff !important;
    background: linear-gradient(135deg,#1464e8,#0b55d9) !important;
}

/* 画像を少し大きく見せる */
[data-testid="stHorizontalBlock"] {
    max-width: 1320px !important;
}
.login-final-title {
    max-width: 1320px !important;
}
[data-testid="stHorizontalBlock"] img {
    border-radius: 18px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ログイン最終修正版：画像の横にID/PWを配置 */
.login-final-title {
    max-width: 1180px;
    margin: 34px auto 20px auto;
    display:flex;
    align-items:center;
    gap:12px;
    color:#ffffff;
    font-size:30px;
    font-weight:950;
}
.login-final-icon {
    width:42px;
    height:42px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    border-radius:13px;
    background:#ffffff;
}
[data-testid="stHorizontalBlock"] {
    max-width:1180px;
    margin-left:auto;
    margin-right:auto;
}
.login-side-head {
    background:#ffffff;
    color:#0f172a;
    border-radius:26px 26px 0 0;
    padding:44px 46px 8px 46px;
    border:1px solid #e2e8f0;
    border-bottom:none;
}
.login-side-logo {
    color:#0b3a88;
    font-size:24px;
    font-weight:950;
    margin-bottom:44px;
}
.login-side-title {
    font-size:30px;
    font-weight:950;
    margin-bottom:12px;
}
.login-side-desc {
    color:#475569;
    font-size:16px;
    font-weight:750;
    margin-bottom:20px;
}
[data-testid="stForm"] {
    background:#ffffff !important;
    border:1px solid #e2e8f0 !important;
    border-top:none !important;
    border-radius:0 0 26px 26px !important;
    padding:0 46px 46px 46px !important;
    box-shadow:none !important;
}
[data-testid="stForm"] label {
    color:#334155 !important;
    font-weight:850 !important;
}
[data-testid="stForm"] input {
    background:#ffffff !important;
    border:1px solid #dbe3ef !important;
    color:#0f172a !important;
    border-radius:14px !important;
    min-height:54px !important;
}
[data-testid="stForm"] button {
    width:100%;
    min-height:56px;
    margin-top:16px;
    border-radius:14px !important;
    background:linear-gradient(135deg,#1464e8,#0b55d9) !important;
    color:#ffffff !important;
    border:none !important;
    font-size:18px !important;
    font-weight:950 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ログイン真完成版 */
.login-page-wrap {
    max-width: 1280px;
    margin: 42px auto 24px auto;
}
.login-card-true {
    background: #ffffff;
    border-radius: 30px;
    padding: 0;
    box-shadow: 0 28px 80px rgba(2, 8, 23, .38);
    border: 1px solid rgba(226,232,240,.9);
    overflow: hidden;
}
.login-robot-photo {
    height: 100%;
    min-height: 520px;
    background: #eaf3ff;
    overflow: hidden;
}
.login-robot-photo img {
    width: 100%;
    height: 100%;
    min-height: 520px;
    object-fit: cover;
    object-position: center center;
    display: block;
}
.login-form-head {
    padding: 54px 54px 6px 42px;
}
.login-logo-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 54px;
}
.login-mini-icon {
    width: 40px;
    height: 40px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    background: #eff6ff;
    font-size: 22px;
}
.login-product-name {
    color: #0b3a88;
    font-size: 28px;
    font-weight: 950;
    letter-spacing: .01em;
}
.login-title-main {
    color: #0f172a;
    font-size: 30px;
    font-weight: 950;
    margin-bottom: 14px;
}
.login-desc-main {
    color: #475569;
    font-size: 16px;
    font-weight: 750;
    margin-bottom: 22px;
}
.login-card-true [data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 54px 54px 42px !important;
}
.login-card-true label {
    color: #334155 !important;
    font-weight: 850 !important;
}
.login-card-true input {
    background: #ffffff !important;
    border: 1px solid #dbe3ef !important;
    color: #0f172a !important;
    border-radius: 14px !important;
    min-height: 54px !important;
    box-shadow: 0 2px 10px rgba(15,23,42,.05) !important;
}
.login-card-true [data-testid="stForm"] button {
    width: 100%;
    min-height: 58px;
    margin-top: 18px;
    border-radius: 14px !important;
    background: linear-gradient(135deg, #1464e8, #0b55d9) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 18px !important;
    font-weight: 950 !important;
    box-shadow: 0 14px 30px rgba(37,99,235,.25) !important;
}
.login-card-true [data-testid="stForm"] button:hover {
    transform: translateY(-1px);
    filter: brightness(1.03);
}
@media (max-width: 900px) {
    .login-page-wrap { margin: 18px auto; }
    .login-card-true { border-radius: 22px; }
    .login-robot-photo { min-height: 320px; }
    .login-robot-photo img { min-height: 320px; }
    .login-form-head { padding: 30px 28px 4px 28px; }
    .login-logo-row { margin-bottom: 28px; }
    .login-product-name { font-size: 22px; }
    .login-card-true [data-testid="stForm"] { padding: 0 28px 32px 28px !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.stApp {
  background:
    radial-gradient(circle at 6% 3%, rgba(37,99,235,.15), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 46%, #eef6ff 100%) !important;
}
.v2-topbar {
  display:flex; align-items:center; justify-content:space-between; gap:18px;
  padding:14px 18px; margin:10px 0 16px 0; border-radius:20px;
  background:linear-gradient(135deg,#0b3a88,#1268de); color:#fff;
  border:1px solid rgba(255,255,255,.16); box-shadow:0 12px 32px rgba(15,80,180,.20);
}
.v2-brand {display:flex; align-items:center; gap:12px;}
.v2-logo-img {width:44px; height:44px; border-radius:13px; object-fit:cover; background:#fff;}
.v2-logo-fallback {width:44px; height:44px; border-radius:13px; display:inline-flex; align-items:center; justify-content:center; background:rgba(255,255,255,.14);}
.v2-brand-title {font-size:27px; font-weight:950; letter-spacing:.02em;}
.v2-brand-sub {font-size:13px; font-weight:800; color:#dbeafe; margin-top:2px;}
.v2-user-pill {padding:8px 12px; border-radius:999px; background:rgba(255,255,255,.14); font-weight:850; border:1px solid rgba(255,255,255,.20);}
.v2-login-copy {padding:18px 20px; border-radius:22px; background:rgba(15,23,42,.55); border:1px solid rgba(148,163,184,.18); margin-top:14px;}
.v2-eyebrow {color:#93c5fd; font-weight:900; font-size:14px;}
.v2-login-title {color:#fff; font-size:26px; font-weight:950; line-height:1.3; margin-top:6px;}
.v2-login-desc {color:#cbd5e1; font-weight:700; line-height:1.75; margin-top:10px;}
.v2-section-title {font-size:28px; font-weight:950; color:#fff; margin:18px 0 12px 0;}
.v2-card {background:rgba(255,255,255,.96); border-radius:18px; padding:18px; box-shadow:0 12px 28px rgba(2,6,23,.16); border:1px solid rgba(226,232,240,.8); min-height:118px;}
.v2-card-label {font-size:13px; color:#334155; font-weight:900;}
.v2-card-num {font-size:30px; line-height:1.1; font-weight:950; color:#0b3a88; margin-top:10px; word-break:break-word;}
.v2-card-num.small {font-size:18px; line-height:1.3;}
.v2-card-sub {font-size:12px; color:#64748b; font-weight:800; margin-top:8px;}
.v2-quick {display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin:14px 0 20px 0;}
.v2-quick-item {background:rgba(255,255,255,.08); border:1px solid rgba(148,163,184,.18); color:#dbeafe; border-radius:16px; padding:13px 12px; font-weight:900; text-align:center;}
.v2-loading {padding:14px 16px; margin:10px 0 18px 0; border-radius:20px; background:rgba(15,23,42,.82); border:1px solid rgba(148,163,184,.22); color:#fff;}
.v2-loading-title {font-size:17px; font-weight:950;}
.v2-loading-bar {position:relative; overflow:hidden; height:8px; max-width:320px; background:rgba(255,255,255,.14); border-radius:999px; margin-top:10px;}
.v2-loading-bar span {position:absolute; inset:0; width:40%; background:linear-gradient(90deg,#60a5fa,#22d3ee); border-radius:999px; animation:v2Move 1.25s infinite ease-in-out;}
@keyframes v2Move {0%{transform:translateX(-100%);}100%{transform:translateX(260%);}}
.stButton > button {border-radius:16px !important; font-weight:850 !important;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#071a38,#0a2a58) !important;}
</style>
""", unsafe_allow_html=True)
if not check_login():
    if st.session_state.get("authenticated", False):
        st.rerun()
    st.stop()


with st.sidebar:
    st.markdown("## 出荷ラクっと Cloud")
    if asset_exists(ROBOT_ICON_IMAGE):
        st.image(str(ROBOT_ICON_IMAGE), width=72)
    st.markdown("---")
    st.markdown("### メニュー")
    st.markdown(
        """
        <div class="side-link-menu">
            <a href="#dashboard">🏠 ダッシュボード</a>
            <a href="#csv-import">📄 CSV取込</a>
            <a href="#rule-settings">🔄 変換ルール設定</a>
            <a href="#ship-date">📅 出荷日設定</a>
            <a href="#template-settings">🧩 テンプレート設定</a>
            <a href="#product-master">📦 商品マスタ管理</a>
            <a href="#admin-users">👤 ユーザー管理</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("データ取込後に出る項目は、画面内で操作します。")

manager = TemplateManager()
selected_template = manager.render_selector_and_sync()

logout_col1, logout_col2 = st.columns([6, 1])
with logout_col1:
    st.caption(f"ログイン中: {st.session_state.get('user_display_name', st.session_state.get('user_id', ''))} ({st.session_state.get('user_role', 'client')})")
with logout_col2:
    if st.button("ログアウト"):
        clear_runtime_state_for_logout()
        st.rerun()

st.markdown('<div id="dashboard"></div>', unsafe_allow_html=True)

if USE_POSTGRES:
    st.caption("保存先: Render Postgres")
else:
    st.caption("保存先: 一時ファイル（DATABASE_URL未設定）")
render_v2_topbar()
render_v2_dashboard_summary()
# render_v2_quick_nav()  # 非表示

with st.expander("▼ 日付対応形式", expanded=False):
    st.caption("YYYY/MM/DD, YYYY-MM-DD, YYYYMMDD, YYYY-MM-DD HH:MM:SS, Unix timestamp秒/ミリ秒, Excelシリアル値")

# 現在設定サマリーは上部カードと重複するため非表示

render_admin_user_management()

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

if st.session_state.pop("template_name_input_clear_next", False):
    selected_template = manager.NEW_LABEL

template_name_input_default = "" if selected_template == manager.NEW_LABEL else selected_template
template_name_input = st.text_input("保存するテンプレート名", value=template_name_input_default, key=f"template_name_input_{gen}")

st.markdown('<div id="csv-import"></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("ファイルを選択（CSV / Excel）", type=["csv", "xlsx"], key=f"uploader_{gen}")
df = None
columns = []
if uploaded_file:
    with st.spinner("ファイル読込中…"):
        file_bytes = uploaded_file.getvalue()
        df = read_uploaded_file_cached(file_bytes, uploaded_file.name)
    columns = list(df.columns)
    st.caption(f"読込完了: {len(df):,}件 / {len(columns)}列")


st.markdown('<div id="code-convert"></div>', unsafe_allow_html=True)
st.markdown('<div id="rule-settings"></div>', unsafe_allow_html=True)
with st.expander("▼ 変換ルール設定", expanded=False):
    st.subheader("変換ルール作成・編集")
    st.caption("保存ボタンはこのブロック下部の「💾 変換ルール保存」です。")
    active_rule_message = get_rule_state("rule_saved_message", "")
    if active_rule_message:
        st.success(active_rule_message)
        set_rule_state("rule_saved_message", "")

    rules_master = load_rules()
    visible_rule_names = ["（新規作成）"] + list_rule_names_for_user(rules_master)

    pending_rule_target = get_rule_state("pending_rule_target", None)
    if pending_rule_target is not None:
        st.session_state[user_rule_state_key("rule_target_widget")] = pending_rule_target if pending_rule_target in visible_rule_names else "（新規作成）"
        set_rule_state("pending_rule_target", None)

    rule_target = st.selectbox("編集する変換ルール", visible_rule_names, key=user_rule_state_key("rule_target_widget"))

    current_last_target = get_rule_state("last_rule_target", None)
    if rule_target != current_last_target:
        set_rule_state("last_rule_target", rule_target)
        if rule_target == "（新規作成）":
            set_rule_state("rule_edit_rows", [{"変換前": "", "変換後": ""}])
            set_rule_state("rule_edit_name", "")
            set_rule_state("rule_edit_type", "通常変換")
            set_rule_state("rule_lookup_from", "商品コード")
            set_rule_state("rule_lookup_to", "品名")
        else:
            rule_payload = normalize_rule_definition(rules_master.get(rule_target, {}))
            rows = [{"変換前": str(k), "変換後": str(v)} for k, v in rule_payload.get("mapping", {}).items()]
            if not rows:
                rows = [{"変換前": "", "変換後": ""}]
            set_rule_state("rule_edit_rows", rows)
            set_rule_state("rule_edit_name", rule_target)
            set_rule_state("rule_edit_type", "商品マスタ参照変換" if rule_payload.get("type") == "master_lookup" else "通常変換")
            set_rule_state("rule_lookup_from", rule_payload.get("lookup_from", "商品コード"))
            set_rule_state("rule_lookup_to", rule_payload.get("lookup_to", "品名"))
        set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
        st.rerun()

    edit_name = get_rule_state("rule_edit_name", "" if rule_target == "（新規作成）" else rule_target)
    edit_rows = get_rule_state("rule_edit_rows", [{"変換前": "", "変換後": ""}])
    if not edit_rows:
        edit_rows = [{"変換前": "", "変換後": ""}]
    rule_form_version = get_rule_state("rule_form_version", 0)

    st.caption("変換ルールはフォーム送信式です。通常変換に加えて、商品マスタ参照変換も作成できます。")

    rule_type_options = ["通常変換", "商品マスタ参照変換"]
    current_rule_type = get_rule_state("rule_edit_type", "通常変換")
    if current_rule_type not in rule_type_options:
        current_rule_type = "通常変換"

    rule_type = st.selectbox(
        "ルール種類",
        rule_type_options,
        index=rule_type_options.index(current_rule_type),
        key=user_rule_state_key(f"rule_type_selector_{rule_form_version}")
    )

    if rule_type != current_rule_type:
        set_rule_state("rule_edit_type", rule_type)
        set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
        st.rerun()

    with st.form(user_rule_state_key(f"rule_edit_form_{rule_form_version}"), clear_on_submit=False):
        new_rule_name = st.text_input("新規ルール名 / 保存名", value=edit_name, key=user_rule_state_key(f"rule_name_form_{rule_form_version}"))

        submitted_rows = []
        lookup_from = get_rule_state("rule_lookup_from", "商品コード")
        lookup_to = get_rule_state("rule_lookup_to", "品名")

        if rule_type == "通常変換":
            for i, row in enumerate(edit_rows):
                c1, c2 = st.columns(2)
                with c1:
                    before_val = st.text_input(f"変換前_{i}", value=row.get("変換前", ""), key=user_rule_state_key(f"rule_form_before_{rule_form_version}_{i}"))
                with c2:
                    after_val = st.text_input(f"変換後_{i}", value=row.get("変換後", ""), key=user_rule_state_key(f"rule_form_after_{rule_form_version}_{i}"))
                submitted_rows.append({"変換前": before_val, "変換後": after_val})
        else:
            st.caption("商品マスタのある列を検索キーにして、別の列の値を返します。例: 品名→商品コード、商品コード→品名")
            pm_columns = PRODUCT_MASTER_COLUMNS.copy()
            lc1, lc2 = st.columns(2)
            with lc1:
                lookup_from = st.selectbox(
                    "商品マスタの検索列",
                    pm_columns,
                    index=pm_columns.index(get_rule_state("rule_lookup_from", "商品コード")) if get_rule_state("rule_lookup_from", "商品コード") in pm_columns else 0,
                    key=user_rule_state_key(f"rule_lookup_from_{rule_form_version}")
                )
            with lc2:
                lookup_to = st.selectbox(
                    "商品マスタの返却列",
                    pm_columns,
                    index=pm_columns.index(get_rule_state("rule_lookup_to", "品名")) if get_rule_state("rule_lookup_to", "品名") in pm_columns else 1,
                    key=user_rule_state_key(f"rule_lookup_to_{rule_form_version}")
                )

        act1, act2, act3, act4 = st.columns(4)
        add_row_submit = act1.form_submit_button("行追加")
        remove_row_submit = act2.form_submit_button("最終行削除")
        save_rule_submit = act3.form_submit_button("💾 変換ルール保存")
        delete_rule_submit = act4.form_submit_button("🗑️ 変換ルール削除")

    if add_row_submit:
        if rule_type == "通常変換":
            submitted_rows.append({"変換前": "", "変換後": ""})
            set_rule_state("rule_edit_rows", submitted_rows)
        set_rule_state("rule_edit_name", new_rule_name)
        set_rule_state("rule_edit_type", rule_type)
        set_rule_state("rule_lookup_from", lookup_from)
        set_rule_state("rule_lookup_to", lookup_to)
        set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
        st.rerun()

    if remove_row_submit:
        if rule_type == "通常変換":
            if len(submitted_rows) > 1:
                submitted_rows = submitted_rows[:-1]
            else:
                submitted_rows = [{"変換前": "", "変換後": ""}]
            set_rule_state("rule_edit_rows", submitted_rows)
        set_rule_state("rule_edit_name", new_rule_name)
        set_rule_state("rule_edit_type", rule_type)
        set_rule_state("rule_lookup_from", lookup_from)
        set_rule_state("rule_lookup_to", lookup_to)
        set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
        st.rerun()

    if save_rule_submit:
        name = new_rule_name.strip()
        if name == "":
            st.error("ルール名を入力してください")
        else:
            if rule_type == "商品マスタ参照変換":
                rule_payload = {
                    "__rule_type__": "master_lookup",
                    "lookup_from": lookup_from,
                    "lookup_to": lookup_to,
                }
                display_desc = f"商品マスタ参照（{lookup_from}→{lookup_to}）"
                saved_rows = [{"変換前": "", "変換後": ""}]
            else:
                clean_rows = []
                for row in submitted_rows:
                    b = str(row.get("変換前", "")).strip()
                    a = str(row.get("変換後", "")).strip()
                    if b != "" or a != "":
                        clean_rows.append({"変換前": b, "変換後": a})
                if not clean_rows:
                    clean_rows = [{"変換前": "", "変換後": ""}]
                rule_payload = rule_rows_to_dict(clean_rows)
                display_desc = "通常変換"
                saved_rows = clean_rows

            with st.spinner("変換ルール保存中…"):
                save_rule_entry(name, rule_payload)
            set_rule_state("rule_saved_message", f"変換ルール『{name}』を保存できました。種類: {display_desc}")
            set_rule_state("rule_edit_rows", saved_rows)
            set_rule_state("rule_edit_name", name)
            set_rule_state("rule_edit_type", rule_type)
            set_rule_state("rule_lookup_from", lookup_from)
            set_rule_state("rule_lookup_to", lookup_to)
            set_rule_state("last_rule_target", name)
            set_rule_state("pending_rule_target", name)
            set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
            st.rerun()

    if delete_rule_submit:
        if rule_target == "（新規作成）":
            st.error("削除するルールを選んでください")
        else:
            with st.spinner("変換ルール削除中…"):
                delete_rule_entry(rule_target)
            set_rule_state("rule_saved_message", f"変換ルール『{rule_target}』を削除できました。")
            set_rule_state("rule_edit_rows", [{"変換前": "", "変換後": ""}])
            set_rule_state("rule_edit_name", "")
            set_rule_state("last_rule_target", "（新規作成）")
            set_rule_state("pending_rule_target", "（新規作成）")
            set_rule_state("rule_form_version", get_rule_state("rule_form_version", 0) + 1)
            st.rerun()


st.markdown('<div id="ship-date"></div>', unsafe_allow_html=True)
with st.expander("▼ 出荷日設定", expanded=False):
    st.subheader("出荷日逆算設定")
    st.caption("指定日から出荷日を自動計算する設定です。保存後、「この設定を使用」を押すと変換時の出荷日に反映されます。")
    if st.session_state.get("ship_date_setting_success_message"):
        st.success(st.session_state["ship_date_setting_success_message"])
        st.session_state["ship_date_setting_success_message"] = ""

    ship_owner = current_product_master_owner()
    ship_store = load_ship_date_store(ship_owner)
    ship_pattern_names = ["（使用しない）", "（新規設定）"] + sorted(list(ship_store.get("patterns", {}).keys()))
    ship_active_name = ship_store.get("active_name", "（使用しない）")
    if ship_active_name not in ship_pattern_names:
        ship_active_name = "（使用しない）"

    sd1, sd2 = st.columns([2, 2])
    with sd1:
        selected_ship_pattern = st.selectbox(
            "使用・編集する出荷日設定",
            ship_pattern_names,
            index=ship_pattern_names.index(ship_active_name),
            key=f"ship_date_pattern_select_{gen}"
        )
    with sd2:
        ship_setting_name = st.text_input(
            "出荷日設定名",
            value="" if selected_ship_pattern in ["（使用しない）", "（新規設定）"] else selected_ship_pattern,
            key=f"ship_date_pattern_name_{gen}_{selected_ship_pattern}"
        )

    ship_cfg = default_ship_date_setting() if selected_ship_pattern in ["（使用しない）", "（新規設定）"] else load_ship_date_setting(ship_owner, selected_ship_pattern)
    if ship_cfg is None:
        ship_cfg = default_ship_date_setting()

    with st.form(f"ship_date_setting_form_{gen}_{selected_ship_pattern}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            days_before = st.number_input(
                "指定日がある場合：指定日の何日前を出荷日にしますか",
                min_value=0,
                max_value=30,
                value=int(ship_cfg.get("days_before", 2)),
                step=1,
            )
        with c2:
            blank_due_days_after_today = st.number_input(
                "指定日が空白の場合：今日から何日後を出荷日にしますか",
                min_value=0,
                max_value=30,
                value=int(ship_cfg.get("blank_due_days_after_today", 1)),
                step=1,
            )

        closed_weekdays = st.multiselect(
            "休業曜日",
            ["月", "火", "水", "木", "金", "土", "日"],
            default=[w for w in ship_cfg.get("closed_weekdays", ["日"]) if w in ["月", "火", "水", "木", "金", "土", "日"]],
        )

        closed_dates = st.text_area(
            "特定休業日（年付き・1行1日、例: 2026-12-27）",
            value=str(ship_cfg.get("closed_dates", "")),
            height=90,
        )

        holiday_mode = st.radio(
            "指定日がある時：出荷日が休業日になる場合",
            ["さらに前日にずらす", "指定日の前日にする"],
            index=["さらに前日にずらす", "指定日の前日にする"].index(ship_cfg.get("holiday_mode", "さらに前日にずらす")),
            horizontal=True,
        )

        blank_due_holiday_mode = st.radio(
            "指定日が空白の時：計算した出荷日が休業日の場合",
            ["当日にする", "翌営業日にする", "前営業日にする"],
            index=["当日にする", "翌営業日にする", "前営業日にする"].index(ship_cfg.get("blank_due_holiday_mode", "翌営業日にする")),
            horizontal=True,
        )

        existing_ship_date_mode = st.radio(
            "すでに出荷日が入っている行の扱い",
            ["既存の出荷日は残す", "すべて再計算する"],
            index=["既存の出荷日は残す", "すべて再計算する"].index(ship_cfg.get("existing_ship_date_mode", "空白だけ自動計算") if ship_cfg.get("existing_ship_date_mode", "空白だけ自動計算") in ["既存の出荷日は残す", "すべて再計算する"] else "既存の出荷日は残す"),
            horizontal=True,
        )

        same_day_alert = st.checkbox(
            "当日出荷になる場合はアラートを出す",
            value=bool(ship_cfg.get("same_day_alert", True)),
        )

        b1, b2, b3 = st.columns(3)
        ship_save = b1.form_submit_button("💾 出荷日設定を保存")
        ship_use = b2.form_submit_button("✅ この出荷日設定を使用")
        ship_delete = b3.form_submit_button("🗑️ 出荷日設定を削除")

    new_ship_cfg = {
        "days_before": int(days_before),
        "blank_due_days_after_today": int(blank_due_days_after_today),
        "closed_weekdays": closed_weekdays,
        "closed_dates": closed_dates,
        "holiday_mode": holiday_mode,
        "blank_due_holiday_mode": blank_due_holiday_mode,
        "existing_ship_date_mode": existing_ship_date_mode,
        "same_day_alert": bool(same_day_alert),
    }

    if ship_save:
        try:
            save_ship_date_setting(ship_setting_name, new_ship_cfg, ship_owner, make_active=True)
            st.session_state["ship_date_setting_success_message"] = f"出荷日設定『{ship_setting_name.strip()}』を保存して使用設定にしました。"
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if ship_use:
        if selected_ship_pattern == "（使用しない）":
            ship_store["active_name"] = "（使用しない）"
            save_ship_date_store(ship_store, ship_owner)
            st.session_state["ship_date_setting_success_message"] = "出荷日自動計算を使用しない設定にしました。"
            st.rerun()
        elif selected_ship_pattern == "（新規設定）":
            st.error("先に設定名を入力して保存してください。")
        else:
            ship_store["active_name"] = selected_ship_pattern
            save_ship_date_store(ship_store, ship_owner)
            st.session_state["ship_date_setting_success_message"] = f"使用する出荷日設定を『{selected_ship_pattern}』に変更しました。"
            st.rerun()

    if ship_delete:
        if selected_ship_pattern in ["（使用しない）", "（新規設定）"]:
            st.error("削除する保存済み設定を選んでください。")
        else:
            delete_ship_date_setting(selected_ship_pattern, ship_owner)
            st.session_state["ship_date_setting_success_message"] = f"出荷日設定『{selected_ship_pattern}』を削除しました。"
            st.rerun()

    active_ship_name_now = load_ship_date_store(ship_owner).get("active_name", "（使用しない）")
    st.info(f"現在使用する出荷日設定: {active_ship_name_now}")

st.markdown('<div id="template-settings"></div>', unsafe_allow_html=True)
with st.expander("▼ テンプレート設定", expanded=False):
    st.subheader("テンプレート操作")
    st.caption("現在のマッピング・出力設定を保存する場合は「💾 テンプレート保存」を押してください。")
    if st.session_state["template_save_message"]:
        st.success(st.session_state["template_save_message"])
        st.session_state["template_save_message"] = ""
    if st.session_state["template_delete_message"]:
        st.success(st.session_state["template_delete_message"])
        st.session_state["template_delete_message"] = ""

    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("💾 テンプレート保存"):
            name = template_name_input.strip()
            if name == "":
                st.error("テンプレート名を入力してください")
            else:
                manager.save_current_as(name)
    with tc2:
        if st.button("🗑️ テンプレート削除"):
            if selected_template == manager.NEW_LABEL:
                st.error("削除するテンプレートを選んでください")
            else:
                manager.delete_active(selected_template)


st.markdown('<div id="product-master"></div>', unsafe_allow_html=True)
with st.expander("▼ 商品マスタ管理", expanded=False):
    st.subheader("商品マスタ管理（追加機能）")
    st.caption("商品マスタCSV/Excelを読み込んだ後、「💾 商品マスタを追加・更新」で保存します。")
    pm_success_message = st.session_state.get("product_master_success_message", "")
    if pm_success_message:
        st.success(pm_success_message)
        st.session_state["product_master_success_message"] = ""

    product_master_owner = current_product_master_owner()
    current_pm_df = load_product_master_df(product_master_owner)
    st.caption(f"現在のアカウントの商品マスタ件数: {len(current_pm_df)}件")

    pm_up_col1, pm_up_col2 = st.columns([2, 1])
    with pm_up_col1:
        product_master_file = st.file_uploader("商品マスタCSV / Excelアップロード", type=["csv", "xlsx"], key=f"product_master_uploader_{gen}")
    with pm_up_col2:
        st.caption("必要列: 商品コード / 品名 / 入数 / 温度帯 / 備考")

    if product_master_file is not None:
        with st.spinner("商品マスタ読込中…"):
            pm_file_bytes = product_master_file.getvalue()
            pm_raw_df = read_uploaded_file_cached(pm_file_bytes, product_master_file.name)
        pm_norm_df = normalize_product_master_df(pm_raw_df)
        st.write("商品マスタ取込プレビュー")
        st.dataframe(pm_norm_df.head(20), use_container_width=True)

        if st.button("💾 商品マスタを追加・更新", key=f"save_product_master_{gen}"):
            pm_errors = validate_product_master_df(pm_norm_df)
            if pm_errors:
                st.error("商品マスタを保存できません。")
                for msg in pm_errors:
                    st.write(f"・{msg}")
            else:
                with st.spinner("商品マスタ保存中…"):
                    latest_existing_df = load_product_master_df(product_master_owner)
                    merged_pm_df, add_count, update_count = merge_product_master_df(latest_existing_df, pm_norm_df)
                    save_product_master_df(merged_pm_df, product_master_owner)
                st.session_state["product_master_success_message"] = (
                    f"商品マスタの登録が完了しました。\n\n新規追加：{add_count}件\n更新：{update_count}件\n合計：{len(merged_pm_df)}件"
                )
                st.rerun()

    if not current_pm_df.empty:
        with st.expander(f"現在の商品マスタを見る（{len(current_pm_df)}件）", expanded=False):
            st.dataframe(current_pm_df, use_container_width=True)
            pm_csv = current_pm_df.to_csv(index=False, encoding="utf-8-sig")
            pm_xlsx = dataframe_to_excel_cached(current_pm_df)
            pm_dl1, pm_dl2 = st.columns(2)
            with pm_dl1:
                st.download_button("商品マスタCSVダウンロード", data=pm_csv, file_name="product_master.csv", mime="text/csv", key=f"pm_csv_dl_{gen}")
            with pm_dl2:
                st.download_button("商品マスタExcelダウンロード", data=pm_xlsx, file_name="product_master.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"pm_xlsx_dl_{gen}")



if df is not None:
    try:
        st.subheader("元データ")
        st.dataframe(df.head())

        st.subheader("項目設定")
        st.caption("各項目ごとに、入力列・固定値・変換ルールを設定できます")
        header_cols = st.columns([3, 3, 3, 3])
        for c, lbl in zip(header_cols, ["**項目名**", "**入力列**", "**固定値**", "**変換ルール**"]):
            with c:
                st.markdown(lbl)

        mapping = {}
        fixed_values = {}
        rule_selection = {}

        for field in available_fields:
            cols4 = st.columns([3, 3, 3, 3])
            with cols4[0]:
                st.write(field)
            with cols4[1]:
                options = ["（未選択）", "（空白）"] + columns
                cur = st.session_state["mapping_model"].get(field, "（未選択）")
                if cur not in options:
                    cur = "（未選択）"
                val = st.selectbox(f"{field}_map", options, index=options.index(cur), label_visibility="collapsed", key=f"map_widget_{field}_{gen}")
                st.session_state["mapping_model"][field] = val
                mapping[field] = val
            with cols4[2]:
                val = st.text_input(f"{field}_fixed", value=st.session_state["fixed_values_model"].get(field, ""), label_visibility="collapsed", key=f"fixed_widget_{field}_{gen}")
                st.session_state["fixed_values_model"][field] = val
                fixed_values[field] = val
            with cols4[3]:
                cur_rule = st.session_state["rule_selection_model"].get(field, "（なし）")
                field_rule_options = ["（なし）"] + list_rule_names_for_user(rules_master)
                if cur_rule not in field_rule_options:
                    cur_rule = "（なし）"
                val = st.selectbox(f"{field}_rule", field_rule_options, index=field_rule_options.index(cur_rule), label_visibility="collapsed", key=f"rule_widget_{field}_{gen}")
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
                    if checked:
                        selected_output_fields.append(field)

            current_order = [f for f in st.session_state["ordered_output_fields_model"] if f in selected_output_fields]
            for f in selected_output_fields:
                if f not in current_order:
                    current_order.append(f)
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
            hh = st.columns([1, 4, 4, 2])
            for c, lbl in zip(hh, ["**順番**", "**項目名**", "**出力列名**", "**移動**"]):
                with c:
                    st.markdown(lbl)

            for idx, field in enumerate(st.session_state["ordered_output_fields_model"], start=1):
                display_name = st.session_state["rename_fields_model"].get(field, field)
                c1, c2, c3, c4 = st.columns([1, 4, 4, 2])
                with c1:
                    st.markdown(f"**{idx}**")
                with c2:
                    st.write(field)
                with c3:
                    st.write(display_name)
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
            with st.spinner("変換中…"):
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

                active_ship_store = load_ship_date_store(current_product_master_owner())
                active_ship_name = active_ship_store.get("active_name", "（使用しない）")
                active_ship_cfg = load_ship_date_setting(current_product_master_owner(), active_ship_name) if active_ship_name != "（使用しない）" else None
                if active_ship_cfg is not None:
                    common_df, ship_alerts = apply_ship_date_setting_to_df(common_df, active_ship_cfg)
                    st.session_state["ship_date_alerts"] = ship_alerts
                else:
                    st.session_state["ship_date_alerts"] = []

                for field, rule_name in rule_selection.items():
                    if rule_name != "（なし）" and field in common_df.columns:
                        common_df[field] = apply_rule(common_df[field], get_rule_payload_by_name(rules_master, rule_name))

                if mode == "通常モード":
                    if len(ordered_output_fields) == 0:
                        st.error("出力項目を1つ以上選んでください")
                        st.stop()

                    missing = [
                        k for k in ordered_output_fields
                        if st.session_state["output_flags_model"].get(k, False)
                        and st.session_state["mapping_model"].get(k, "（未選択）") == "（未選択）"
                        and str(st.session_state["fixed_values_model"].get(k, "")).strip() == ""
                    ]
                    if missing:
                        st.error(f"未選択の項目があります: {', '.join(missing)}")
                        st.stop()

                    output_df = common_df[ordered_output_fields].copy()
                    rename_dict = {field: (str(st.session_state["rename_fields_model"].get(field, field)).strip() or field) for field in ordered_output_fields}
                    output_df = output_df.rename(columns=rename_dict)
                else:
                    output_df = build_yamato_df(common_df)
                    yamato_missing = validate_yamato_required(output_df)
                    if yamato_missing:
                        st.error("ヤマト必須項目が不足しています")
                        for col in yamato_missing:
                            st.write(f"・{col}")
                        st.stop()

                    yamato_errors, yamato_warnings = validate_yamato_format(output_df)
                    if yamato_errors:
                        st.error("ヤマト形式エラーがあります")
                        for msg in yamato_errors:
                            st.write(f"・{msg}")
                        st.stop()
                    if yamato_warnings:
                        st.warning("ヤマト形式の警告があります")
                        for msg in yamato_warnings:
                            st.write(f"・{msg}")

            output_df_for_state = output_df.copy()
            for col in output_df_for_state.columns:
                output_df_for_state[col] = output_df_for_state[col].fillna("").astype(str)
            st.session_state["converted_output_df_json"] = output_df_for_state.to_json(orient="split", force_ascii=False)
            st.session_state["converted_output_success_message"] = "変換完了！"

            st.success("変換完了！")
            if st.session_state.get("ship_date_alerts"):
                for msg in st.session_state["ship_date_alerts"]:
                    st.warning(msg)
            st.subheader("変換後データ")
            st.dataframe(output_df)

            if show_transform_detail:
                st.subheader("項目ごとの変換イメージ分析")
                preview_list = build_all_transform_previews(df, common_df, mapping, fixed_values, rule_selection, rules_master)
                if preview_list:
                    summary_rows = []
                    for item in preview_list:
                        summary_rows.append({
                            "項目": item["field"],
                            "入力列": item["selected_col"],
                            "固定値": item["fixed_value"],
                            "変換ルール": item["rule_name"],
                            "変換件数": item["changed_count"],
                            "元値種類数": item["source_unique_count"],
                            "未変換値数": item["unconverted_count"],
                            "ルール漏れ候補数": item["leak_count"],
                        })
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            csv_data = dataframe_to_csv_cached(output_df)
            excel_data = dataframe_to_excel_cached(output_df)
            dc1, dc2 = st.columns(2)
            with dc1:
                st.download_button("CSVダウンロード", data=csv_data, file_name="output.csv", mime="text/csv")
            with dc2:
                st.download_button("Excelダウンロード", data=excel_data, file_name="output.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# 変換済みデータを保持して、別ボタン押下時にも消えないようにする
saved_output_json = st.session_state.get("converted_output_df_json", "")
if saved_output_json:
    try:
        saved_output_df = pd.read_json(StringIO(saved_output_json), orient="split")
        st.subheader("変換後データ（保持中）")
        if st.session_state.get("converted_output_success_message"):
            st.success(st.session_state["converted_output_success_message"])
            st.session_state["converted_output_success_message"] = ""
        st.dataframe(saved_output_df)

        st.markdown('<div id="picklist-settings"></div>', unsafe_allow_html=True)
        with st.expander("▼ ピッキング設定", expanded=False):
            st.subheader("ピッキングリスト設定")
            st.caption("ピッキング設定を残す場合は「💾 新規保存 / 上書き保存」、PDF作成に使う場合は「✅ この設定を使用」を押してください。")
            if st.session_state.get("picklist_mapping_success_message"):
                st.success(st.session_state["picklist_mapping_success_message"])
                st.session_state["picklist_mapping_success_message"] = ""

            pick_owner = current_product_master_owner()
            st.caption(f"ピッキングリストで使う項目を、変換後データのどの列にするか設定します。固定値や空白も指定できます。現在の設定保存先アカウント: {pick_owner}")

            pick_store = load_picklist_mapping_store(pick_owner)
            pattern_names = ["（新規設定）"] + sorted(list(pick_store.get("patterns", {}).keys()))
            active_name = pick_store.get("active_name", "（新規設定）")
            if active_name not in pattern_names:
                active_name = "（新規設定）"

            top1, top2 = st.columns([2, 2])
            with top1:
                selected_pattern = st.selectbox("保存済みピッキング設定", pattern_names, index=pattern_names.index(active_name), key=f"pick_pattern_select_{gen}")
            last_pattern = st.session_state.get("picklist_selected_pattern_last", "")
            if selected_pattern != last_pattern:
                st.session_state["picklist_selected_pattern_last"] = selected_pattern
                st.session_state["picklist_pattern_form_version"] = st.session_state.get("picklist_pattern_form_version", 0) + 1

            form_ver = st.session_state.get("picklist_pattern_form_version", 0)
            pattern_key_tag = selected_pattern.replace(" ", "_")

            with top2:
                pattern_save_name = st.text_input(
                    "ピッキング設定名",
                    value="" if selected_pattern == "（新規設定）" else selected_pattern,
                    key=f"pick_pattern_name_{gen}_{pattern_key_tag}_{form_ver}"
                )

            current_cfg = default_picklist_mapping() if selected_pattern == "（新規設定）" else load_picklist_mapping(pick_owner, selected_pattern)
            source_options = ["（空白）"] + [str(c) for c in saved_output_df.columns.tolist()]

            with st.form(f"picklist_mapping_form_{gen}_{form_ver}", clear_on_submit=False):
                st.markdown("**ピッキングリスト用マッピング一覧**")
                h1, h2, h3 = st.columns([2, 3, 3])
                with h1:
                    st.markdown("**項目**")
                with h2:
                    st.markdown("**CSV列**")
                with h3:
                    st.markdown("**固定値**")

                new_cfg = {}
                for field, optional in PICKLIST_MAPPING_FIELDS:
                    c1, c2, c3 = st.columns([2, 3, 3])
                    with c1:
                        label = f"{field}（空白OK）" if optional else field
                        st.write(label)
                    with c2:
                        cur_source = current_cfg.get(field, {}).get("source", "（空白）")
                        if cur_source not in source_options:
                            cur_source = "（空白）"
                        src_val = st.selectbox(
                            f"{field}_pick_src",
                            source_options,
                            index=source_options.index(cur_source),
                            key=f"pick_src_{field}_{gen}_{pattern_key_tag}_{form_ver}",
                            label_visibility="collapsed",
                        )
                    with c3:
                        fixed_val = st.text_input(
                            f"{field}_pick_fixed",
                            value=current_cfg.get(field, {}).get("fixed", ""),
                            key=f"pick_fix_{field}_{gen}_{pattern_key_tag}_{form_ver}",
                            label_visibility="collapsed",
                        )
                    new_cfg[field] = {"source": src_val, "fixed": fixed_val}

                a1, a2, a3 = st.columns(3)
                save_as_submit = a1.form_submit_button("💾 新規保存 / 上書き保存")
                set_active_submit = a2.form_submit_button("✅ この設定を使用")
                delete_submit = a3.form_submit_button("🗑️ 設定削除")

            if save_as_submit:
                try:
                    save_name = pattern_save_name.strip()
                    if save_name == "":
                        st.error("保存する設定名を入力してください。")
                    else:
                        save_picklist_mapping(new_cfg, pick_owner, save_name, make_active=True)
                        st.session_state["picklist_mapping_success_message"] = f"ピッキング設定『{save_name}』を保存できました。"
                        st.rerun()
                except Exception as e:
                    st.error(str(e))

            if set_active_submit:
                if selected_pattern == "（新規設定）":
                    st.error("使用する保存済み設定を選んでください。")
                else:
                    pick_store["active_name"] = selected_pattern
                    save_picklist_mapping_store(pick_store, pick_owner)
                    st.session_state["picklist_mapping_success_message"] = f"使用するピッキング設定を『{pick_store['active_name']}』に変更しました。"
                    st.rerun()

            if delete_submit:
                if selected_pattern == "（新規設定）":
                    st.error("削除する設定を選んでください。")
                else:
                    delete_picklist_mapping(pick_owner, selected_pattern)
                    st.session_state["picklist_mapping_success_message"] = f"ピッキング設定『{selected_pattern}』を削除しました。"
                    st.rerun()

        st.subheader("ピッキングリストPDF作成（追加機能）")
        active_pattern_name = load_picklist_mapping_store(pick_owner).get("active_name", "（新規設定）")
        st.caption(f"現在使用する設定: {active_pattern_name}")

        picklist_pdf_bytes = None
        picklist_pdf_success = ""

        pick_pdf_col1, pick_pdf_col2 = st.columns([1, 2])
        with pick_pdf_col1:
            if st.button("ピッキングリスト作成", key=f"picklist_pdf_build_saved_{gen}"):
                try:
                    with st.spinner("ピッキングリストPDF作成中…"):
                        pm_df_now = load_product_master_df(current_product_master_owner())
                        effective_cfg = load_picklist_mapping(pick_owner, active_pattern_name) if active_pattern_name != "（新規設定）" else new_cfg
                        picklist_pdf_df, picklist_warnings = build_picklist_dataframe(saved_output_df, pm_df_now, effective_cfg)
                        picklist_pdf_bytes = build_picklist_pdf_bytes(picklist_pdf_df)
                        st.session_state["picklist_pdf_warnings"] = picklist_warnings
                        picklist_pdf_success = f"ピッキングリストPDFを作成できました。受注件数：{picklist_pdf_df['受注番号'].nunique()}件"
                except Exception as e:
                    st.error(str(e))

        with pick_pdf_col2:
            if picklist_pdf_success:
                st.success(picklist_pdf_success)

        picklist_warning_list = st.session_state.get("picklist_pdf_warnings", [])
        if picklist_warning_list:
            for msg in picklist_warning_list:
                st.warning(msg)

        if picklist_pdf_bytes:
            st.download_button(
                "ピッキングリストPDFダウンロード",
                data=picklist_pdf_bytes,
                file_name="picklist.pdf",
                mime="application/pdf",
                key=f"picklist_pdf_dl_saved_{gen}",
            )
    except Exception:
        pass


# ===== FINAL FORCE LIGHT MODE CSS =====
st.markdown("""
<style id="final-force-light-mode">
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#ffffff 0%,#f8fbff 60%,#edf6ff 100%) !important;
    color: #0f172a !important;
}

/* Streamlitメインと全ラッパー */
.main,
.block-container,
section.main,
section[data-testid="stSidebar"],
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stHorizontalBlock"],
.element-container,
div[data-testid="stMarkdownContainer"] {
    background-color: transparent !important;
    color: #0f172a !important;
}

/* sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background: linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}

/* header */
[data-testid="stHeader"] {
    background: rgba(255,255,255,.98) !important;
    border-bottom: 1px solid #e2e8f0 !important;
}

/* 既存v2系 */
.v2-topbar,
.v2-card,
.v2-quick-item,
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.055) !important;
}
.v2-topbar *,
.v2-card *,
.v2-quick-item *,
[data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}

.v2-section-title,
.v2-card-num,
h1,h2,h3,h4,h5,h6 {
    color: #0b3a88 !important;
    opacity: 1 !important;
}

.v2-brand-title {
    background: linear-gradient(135deg,#0b3a88 0%,#2563eb 55%,#22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.v2-brand-sub,
.v2-card-label,
.v2-card-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}

/* Streamlitの入力欄 */
input,
textarea,
[data-baseweb="input"],
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}

/* ボタン */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg,#2563eb 0%,#22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
}
.stButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
}

/* inline styleで濃紺が残るものを直接潰す */
div[style*="#ffffff"],
div[style*="#f8fbff"],
div[style*="#eef6ff"] {
    color: #0f172a !important;
}

div[style*="background:linear-gradient(180deg, #ffffff"],
div[style*="background: linear-gradient(180deg, #ffffff"],
div[style*="background:linear-gradient(135deg, #ffffff"],
div[style*="background: linear-gradient(135deg, #ffffff"] {
    color: #0f172a !important;
}

/* 濃色背景の残骸を検出して白へ */
div[style*="background:linear-gradient(180deg"],
div[style*="background: linear-gradient(180deg"],
div[style*="background:linear-gradient(135deg"],
div[style*="background: linear-gradient(135deg"] {
    background: #ffffff !important;
    color: #0f172a !important;
}

/* ただしログイン画面の true 系は壊しすぎない */
.true-login-page,
.true-brand,
.true-peek-wrap,
.true-peek-wall {
    color: inherit;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
.true-logo-main {
    padding-right: 72px !important;
    overflow: visible !important;
}

.true-logo-cloudmark {
    position: absolute !important;
    right: -58px !important;
    top: -6px !important;
    width: 62px !important;
    height: 38px !important;
    border: none !important;
    background: transparent !important;
    opacity: 1 !important;
}

.true-logo-cloudmark::before {
    content: "" !important;
    position: absolute !important;
    left: 9px !important;
    top: 0 !important;
    width: 40px !important;
    height: 20px !important;
    border: 5px solid #35bfff !important;
    border-bottom: none !important;
    border-radius: 30px 30px 0 0 !important;
    background: transparent !important;
}

.true-logo-cloudmark::after {
    content: "" !important;
    position: absolute !important;
    left: 2px !important;
    top: 20px !important;
    width: 54px !important;
    height: 8px !important;
    border-top: 5px solid #35bfff !important;
    border-radius: 20px !important;
    background: transparent !important;
}

@media (max-width: 980px) {
    .true-logo-cloudmark { display: none !important; }
    .true-logo-main { padding-right: 0 !important; }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #ffffff 0%, #f8fbff 58%, #edf6ff 100%) !important;
    color: #0f172a !important;
}
[data-testid="stHeader"] {
    background: rgba(255,255,255,.96) !important;
    border-bottom: 1px solid #e2e8f0 !important;
}
.main, .block-container, section.main,
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stHorizontalBlock"],
.element-container {
    background: transparent !important;
    color: #0f172a !important;
}
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
h1, h2, h3, h4, h5, h6 {
    color: #0b2f78 !important;
    opacity: 1 !important;
}
.v2-topbar {
    background: #ffffff !important;
    border: 1px solid #dbeafe !important;
    border-radius: 26px !important;
    box-shadow: 0 14px 36px rgba(37,99,235,.10) !important;
    color: #0f172a !important;
}
.v2-topbar * { color: #0f172a !important; opacity: 1 !important; }
.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 55%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
.v2-brand-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}
.v2-user-pill {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}
.v2-section-title {
    color: #0b3a88 !important;
    font-size: 38px !important;
    font-weight: 950 !important;
}
.v2-card, .v2-quick-item, [data-testid="stExpander"],
[data-testid="stDataFrame"], [data-testid="stTable"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.05) !important;
    color: #0f172a !important;
}
.v2-card { border-radius: 24px !important; }
.v2-card *, .v2-quick-item *, [data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
.v2-card-label { color: #475569 !important; font-weight: 850 !important; }
.v2-card-num { color: #0b3a88 !important; font-weight: 950 !important; }
.v2-card-sub { color: #64748b !important; }
.v2-quick-item { border-radius: 18px !important; }
.v2-quick-item, .v2-quick-item * { color: #0b3a88 !important; }
.v2-quick-item:hover { background: #eff6ff !important; }

input, textarea, [data-baseweb="input"], [data-baseweb="select"],
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
}
label, [data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
    opacity: 1 !important;
}
.stButton > button, [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 900 !important;
    box-shadow: 0 10px 24px rgba(37,99,235,.18) !important;
}
.stButton > button *, [data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
    opacity: 1 !important;
}
button[kind="secondary"] {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}
button[kind="secondary"] * { color: #0b3a88 !important; }

/* Cloud横の雲マーク 最終修正版 */
.true-logo-main {
    padding-right: 64px !important;
    overflow: visible !important;
}
.true-logo-cloudmark {
    position: absolute !important;
    right: -50px !important;
    top: -4px !important;
    width: 54px !important;
    height: 34px !important;
    border: none !important;
    background: transparent !important;
    opacity: 1 !important;
}
.true-logo-cloudmark::before {
    content: "" !important;
    position: absolute !important;
    left: 8px !important;
    top: 0 !important;
    width: 36px !important;
    height: 18px !important;
    border: 4px solid #37bfff !important;
    border-bottom: none !important;
    border-radius: 26px 26px 0 0 !important;
    background: transparent !important;
}
.true-logo-cloudmark::after {
    content: "" !important;
    position: absolute !important;
    left: 4px !important;
    top: 18px !important;
    width: 44px !important;
    height: 0 !important;
    border-top: 4px solid #37bfff !important;
    border-radius: 12px !important;
    background: transparent !important;
}
@media (max-width: 980px) {
    .true-logo-cloudmark { display: none !important; }
    .true-logo-main { padding-right: 0 !important; }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* =========================================================
   出荷ラクっと Cloud：既存機能保持 完全版
   - ピッキングリスト / CSV変換 / PDF / 商品マスタ / 出荷日計算 等は残す
   - 雲マークはCSS図形をやめて、安定する ☁ アイコンへ
   - ログイン後も白基調へ
   ========================================================= */

/* ---------- 全体：白〜薄水色 ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 16% 8%, rgba(255,255,255,1), transparent 34%),
        radial-gradient(circle at 86% 4%, rgba(255,255,255,1), transparent 38%),
        linear-gradient(135deg, #ffffff 0%, #f8fbff 58%, #edf6ff 100%) !important;
    color: #0f172a !important;
}

[data-testid="stHeader"] {
    background: rgba(255,255,255,.96) !important;
    border-bottom: 1px solid #e2e8f0 !important;
    backdrop-filter: blur(12px) !important;
}

.main,
.block-container,
section.main,
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stHorizontalBlock"],
.element-container {
    background: transparent !important;
    color: #0f172a !important;
}

.block-container {
    max-width: 1280px !important;
    padding-top: 2rem !important;
}

/* ---------- サイドバー ---------- */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}

[data-testid="stSidebar"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #0b3a88 !important;
}

/* ---------- 見出し・文字 ---------- */
h1, h2, h3, h4, h5, h6 {
    color: #0b2f78 !important;
    opacity: 1 !important;
}

p, span, label, small {
    opacity: 1 !important;
}

/* ---------- ログイン画面：Cloud横アイコン修正 ---------- */
.true-logo-main {
    padding-right: 0 !important;
    overflow: visible !important;
}

/* 崩れていたCSS雲マークは完全に消す */
.true-logo-cloudmark,
.true-logo-cloudmark::before,
.true-logo-cloudmark::after {
    display: none !important;
    content: none !important;
    border: none !important;
}

/* Cloud文字の横に安定するクラウドアイコンを付ける */
.true-logo-cloud::after {
    content: "☁";
    display: inline-block;
    margin-left: 12px;
    font-size: .82em;
    line-height: 1;
    font-style: normal;
    font-weight: 900;
    background: linear-gradient(135deg, #2b7fff 0%, #39c6ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    transform: translateY(-0.10em);
    filter: drop-shadow(0 8px 18px rgba(37,99,235,.18));
}

/* ---------- 上部ブランドバー ---------- */
.v2-topbar {
    background: rgba(255,255,255,.96) !important;
    border: 1px solid #dbeafe !important;
    border-radius: 26px !important;
    box-shadow: 0 14px 36px rgba(37,99,235,.10) !important;
    color: #0f172a !important;
}

.v2-topbar * {
    color: #0f172a !important;
    opacity: 1 !important;
}

.v2-brand-title {
    background: linear-gradient(135deg, #0b3a88 0%, #2563eb 55%, #22a8f0 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.v2-brand-sub {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
}

.v2-user-pill {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}

/* ---------- ダッシュボードカード ---------- */
.v2-section-title {
    color: #0b3a88 !important;
    font-size: 38px !important;
    font-weight: 950 !important;
}

.v2-card,
.v2-quick-item,
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.05) !important;
    color: #0f172a !important;
}

.v2-card {
    border-radius: 24px !important;
}

.v2-card *,
.v2-quick-item *,
[data-testid="stExpander"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}

.v2-card-label {
    color: #475569 !important;
    font-weight: 850 !important;
}

.v2-card-num {
    color: #0b3a88 !important;
    font-weight: 950 !important;
}

.v2-card-sub {
    color: #64748b !important;
}

.v2-quick-item {
    border-radius: 18px !important;
}

.v2-quick-item,
.v2-quick-item * {
    color: #0b3a88 !important;
}

.v2-quick-item:hover {
    background: #eff6ff !important;
}

/* ---------- フォーム・入力欄 ---------- */
input,
textarea,
[data-baseweb="input"],
[data-baseweb="select"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
}

label,
[data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
    opacity: 1 !important;
}

/* ---------- ボタン ---------- */
.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #2563eb 0%, #22a8f0 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 16px !important;
    font-weight: 900 !important;
    box-shadow: 0 10px 24px rgba(37,99,235,.18) !important;
}

.stButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
    opacity: 1 !important;
}

button[kind="secondary"] {
    background: #ffffff !important;
    color: #0b3a88 !important;
    border: 1px solid #bfdbfe !important;
}

button[kind="secondary"] * {
    color: #0b3a88 !important;
}

/* ---------- タブ・ラジオ ---------- */
[role="tab"],
[role="radiogroup"] label {
    color: #0f172a !important;
    opacity: 1 !important;
}

/* ---------- 濃紺・黒背景の残りを白化 ---------- */
[style*="background:#0"],
[style*="background: #0"],
[style*="background-color:#0"],
[style*="background-color: #0"],
[style*="rgb(2, 6, 23)"],
[style*="rgb(15, 23, 42)"] {
    background: #ffffff !important;
    color: #0f172a !important;
}

/* 白文字残りを補正。ただしボタンは白文字維持 */
[style*="color: white"],
[style*="color:#fff"],
[style*="color: #fff"],
[style*="color: rgb(255, 255, 255)"] {
    color: #0f172a !important;
}

.stButton [style*="color: white"],
.stButton [style*="color:#fff"],
.stButton [style*="color: #fff"],
.stButton [style*="color: rgb(255, 255, 255)"],
[data-testid="stFormSubmitButton"] [style*="color: white"],
[data-testid="stFormSubmitButton"] [style*="color:#fff"],
[data-testid="stFormSubmitButton"] [style*="color: #fff"],
[data-testid="stFormSubmitButton"] [style*="color: rgb(255, 255, 255)"] {
    color: #ffffff !important;
}

@media (max-width: 980px) {
    .true-logo-cloud::after {
        display: none !important;
    }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* =========================================================
   Cloud横マーク最終修正：古いCSS雲を完全停止し、☁アイコンだけ表示
   ========================================================= */

/* 古い雲マークを完全に消す */
.true-logo-cloudmark,
.true-logo-cloudmark::before,
.true-logo-cloudmark::after,
.logo-cloudmark,
.logo-cloudmark::before,
.logo-cloudmark::after {
    display: none !important;
    content: none !important;
    border: 0 !important;
    width: 0 !important;
    height: 0 !important;
    opacity: 0 !important;
    visibility: hidden !important;
}

/* Cloud文字の疑似要素で追加していたものも停止 */
.true-logo-cloud::after,
.logo-cloud::after {
    display: none !important;
    content: none !important;
}

/* 新しい安定Cloudアイコン */
.true-cloud-emoji {
    display: inline-block !important;
    margin-left: 14px !important;
    font-size: 0.82em !important;
    line-height: 1 !important;
    font-style: normal !important;
    font-weight: 900 !important;
    vertical-align: top !important;
    transform: translateY(-0.10em) !important;
    background: linear-gradient(135deg, #2b7fff 0%, #39c6ff 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    filter: drop-shadow(0 8px 18px rgba(37,99,235,.18)) !important;
}

/* ロゴの右余白を古い雲用から通常に戻す */
.true-logo-main,
.logo-main {
    padding-right: 0 !important;
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* =========================================================
   ログイン画面微修正
   - PW横の変なグレー/Enter表示対策
   - ログイン後の下部アクション非表示
   ========================================================= */

/* ログイン下部の「または」「SSO」などは非表示 */
.mock-login-footer,
.mock-divider,
.mock-sso,
.run-loader,
.mock-loading,
.run-track,
.run-title,
.run-sub,
.run-bar {
    display: none !important;
}

/* 入力欄全体を白で統一 */
[data-testid="stForm"] [data-testid="stTextInputRootElement"],
[data-testid="stForm"] [data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 18px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}

/* 入力欄の内部レイヤーも白にする */
[data-testid="stForm"] [data-baseweb="input"] > div,
[data-testid="stForm"] [data-testid="stTextInputRootElement"] > div {
    background: #ffffff !important;
}

/* input本体 */
[data-testid="stForm"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    border: none !important;
    box-shadow: none !important;
    min-height: 58px !important;
    font-size: 18px !important;
    padding-left: 18px !important;
}

/* パスワード表示/非表示ボタンの領域を小さく自然に */
[data-testid="stForm"] button[kind="icon"],
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button,
[data-testid="stForm"] [data-baseweb="input"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    width: 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    padding: 0 !important;
    margin-right: 6px !important;
    color: #94a3b8 !important;
}

/* 目アイコンが薄すぎる/枠が出るのを抑える */
[data-testid="stForm"] button[kind="icon"] svg,
[data-testid="stForm"] [data-testid="stTextInputRootElement"] button svg,
[data-testid="stForm"] [data-baseweb="input"] button svg {
    color: #94a3b8 !important;
    fill: #94a3b8 !important;
    opacity: .9 !important;
}

/* Streamlit/BaseWebの余計な右側背景を白に固定 */
[data-testid="stForm"] [data-baseweb="input"] div[role="button"],
[data-testid="stForm"] [data-baseweb="input"] div[aria-hidden="true"] {
    background: transparent !important;
}

/* ブラウザのEnterツールチップっぽい表示が乗る時の見た目崩れを抑える */
[data-testid="stForm"] input:focus {
    outline: none !important;
    box-shadow: none !important;
}

/* ログインボタンは見やすく */
[data-testid="stFormSubmitButton"] button {
    color: #ffffff !important;
}
[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
html {
    scroll-behavior: smooth;
}

.side-link-menu {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 10px;
}

.side-link-menu a {
    display: block;
    text-decoration: none !important;
    background: #ffffff;
    color: #0b3a88 !important;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 14px 16px;
    font-weight: 850;
    box-shadow: 0 6px 18px rgba(37,99,235,.06);
    transition: all .15s ease;
}

.side-link-menu a:hover {
    background: #eff6ff;
    transform: translateY(-1px);
}

/* 万一、前回の押せるボタン版が残っても非表示 */
[data-testid="stSidebar"] .stButton {
    display: none !important;
}

/* アンカー位置がヘッダーに隠れないように */
#dashboard,
#csv-import,
#data-convert,
#code-convert,
#ship-date,
#report-output,
#picklist,
#product-master,
#settings {
    scroll-margin-top: 90px;
}
</style>
""", unsafe_allow_html=True)




st.markdown("""
<style>
.side-link-menu {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 10px;
}
.side-link-menu a {
    display: block;
    text-decoration: none !important;
    background: #ffffff;
    color: #0b3a88 !important;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 14px 16px;
    font-weight: 850;
    box-shadow: 0 6px 18px rgba(37,99,235,.06);
    transition: all .15s ease;
}
.side-link-menu a:hover {
    background: #eff6ff;
    transform: translateY(-1px);
}
#dashboard,
#csv-import,
#rule-settings,
#ship-date,
#template-settings,
#product-master,
#admin-users {
    scroll-margin-top: 96px;
}
[data-testid="stSidebar"] .stButton {
    display: none !important;
}
.v2-quick {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
.block-container{
    padding-top:0.6rem !important;
    padding-bottom:1rem !important;
}

header[data-testid="stHeader"]{
    height:0rem !important;
    background:transparent !important;
}

div[data-testid="stToolbar"]{
    top:0.35rem !important;
}

button[title="View fullscreen"]{
    display:none !important;
}

[data-testid="StyledFullScreenButton"]{
    display:none !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* ===== 上余白を詰める・画像拡大黒ボタン消し ===== */
.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 1rem !important;
}

header[data-testid="stHeader"] {
    height: 0rem !important;
    background: transparent !important;
}

div[data-testid="stToolbar"] {
    top: 0.35rem !important;
}

button[title="View fullscreen"] {
    display: none !important;
}

[data-testid="StyledFullScreenButton"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* 画像右上の黒い拡大ボタンを消す */
[data-testid="stImage"] button,
[data-testid="stImage"] [role="button"],
[data-testid="stImage"] [data-testid="StyledFullScreenButton"],
button[title="View fullscreen"],
button[title="Fullscreen"],
button[aria-label="View fullscreen"],
button[aria-label="Fullscreen"],
button[aria-label="拡大表示"],
button[aria-label="全画面表示"],
[data-testid="StyledFullScreenButton"] {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    pointer-events: none !important;
}

/* プルダウン本体：白背景・濃い文字に固定 */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}

/* 選択中の文字 */
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-testid="stSelectbox"] span,
[data-testid="stSelectbox"] div {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

/* プルダウンの中身 */
[data-baseweb="popover"],
[data-baseweb="popover"] *,
[data-baseweb="menu"],
[data-baseweb="menu"] *,
[role="listbox"],
[role="listbox"] *,
ul[role="listbox"],
ul[role="listbox"] *,
li[role="option"],
li[role="option"] * {
    background-color: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

/* 選択肢 */
[role="option"],
li[role="option"],
[data-baseweb="menu"] li,
[data-baseweb="menu"] div[role="option"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border-radius: 10px !important;
}

/* ホバー・選択中 */
[role="option"]:hover,
li[role="option"]:hover,
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] div[role="option"]:hover,
[aria-selected="true"],
[aria-selected="true"] * {
    background: #eff6ff !important;
    color: #0b3a88 !important;
    -webkit-text-fill-color: #0b3a88 !important;
}

/* ポップアップ外枠 */
[data-baseweb="popover"] > div,
[data-baseweb="menu"] {
    border: 1px solid #dbeafe !important;
    border-radius: 16px !important;
    box-shadow: 0 18px 45px rgba(15,23,42,.12) !important;
}

/* select内の薄い文字を濃く */
.stSelectbox,
.stSelectbox *,
div[data-baseweb="select"] input {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* =========================================================
   プルダウン中身：白文字化を完全補正
   ========================================================= */

/* BaseWeb select popover 全体 */
div[data-baseweb="popover"],
div[data-baseweb="popover"] div,
div[data-baseweb="menu"],
div[data-baseweb="menu"] div,
ul[role="listbox"],
ul[role="listbox"] li,
li[role="option"],
div[role="option"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    opacity: 1 !important;
}

/* 選択肢の中の span / p / div を強制的に濃くする */
li[role="option"] *,
div[role="option"] *,
ul[role="listbox"] *,
div[data-baseweb="menu"] * {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    opacity: 1 !important;
}

/* 選択中・ホバー */
li[role="option"]:hover,
div[role="option"]:hover,
li[aria-selected="true"],
div[aria-selected="true"] {
    background-color: #eff6ff !important;
}

li[role="option"]:hover *,
div[role="option"]:hover *,
li[aria-selected="true"] *,
div[aria-selected="true"] * {
    color: #0b3a88 !important;
    -webkit-text-fill-color: #0b3a88 !important;
}

/* disabledっぽく薄くされるのを解除 */
[aria-disabled="true"],
[aria-disabled="true"] * {
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
    opacity: 1 !important;
}

/* Streamlitがspanに白指定してくるケースをselectポップアップ内だけ上書き */
div[data-baseweb="popover"] span,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] div {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

/* 外枠 */
div[data-baseweb="popover"] > div {
    background: #ffffff !important;
    border: 1px solid #dbeafe !important;
    border-radius: 16px !important;
    box-shadow: 0 18px 45px rgba(15,23,42,.14) !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* 保存するテンプレート名の入力欄を白背景・濃い文字に固定 */
input[aria-label="保存するテンプレート名"],
div[data-testid="stTextInput"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

[data-testid="stTextInputRootElement"] {
    background: #ffffff !important;
    border-color: #cbd5e1 !important;
}
</style>
""", unsafe_allow_html=True)

