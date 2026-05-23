import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO


# =========================
# グラフ用：日本語フォント設定
# =========================
# ローカルWindowsでは Yu Gothic、
# Streamlit Cloudでは packages.txt で入れる Noto Sans CJK JP を使う想定
available_fonts = [font.name for font in fm.fontManager.ttflist]

if "Noto Sans CJK JP" in available_fonts:
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
elif "Yu Gothic" in available_fonts:
    plt.rcParams["font.family"] = "Yu Gothic"
else:
    plt.rcParams["font.family"] = "DejaVu Sans"

plt.rcParams["axes.unicode_minus"] = False


# =========================
# PDF用：日本語フォント設定
# =========================
# まずはWindowsローカル用に Yu Gothic を試す
# Streamlit Cloudではこのフォントが存在しない可能性があるため、失敗時はHelveticaに戻す
try:
    pdfmetrics.registerFont(TTFont("YuGothic", "C:/Windows/Fonts/YuGothM.ttc"))
    PDF_FONT_NAME = "YuGothic"
except:
    PDF_FONT_NAME = "Helvetica"


# =========================
# 表示名の設定
# =========================
COLUMN_LABELS = {
    "date": "日付",
    "staff_name": "担当者",
    "customer_name": "顧客名",
    "area": "エリア",
    "service_plan": "サービスプラン",
    "revenue": "売上",
    "contracts": "契約数",
    "responses": "反応数",
}

GROUP_OPTIONS = {
    "担当者別": "staff_name",
    "エリア別": "area",
    "サービスプラン別": "service_plan",
}

VALUE_OPTIONS = {
    "売上": "revenue",
    "契約数": "contracts",
    "反応数": "responses",
}


# =========================
# PDF作成関数
# =========================
def create_pdf_report(summary_df, start_date, end_date, group_labels, value_labels, fig):
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal_style = styles["Normal"]

    title_style.fontName = PDF_FONT_NAME
    normal_style.fontName = PDF_FONT_NAME

    elements = []

    elements.append(Paragraph("CSVレポート自動作成デモ", title_style))
    elements.append(Spacer(1, 16))

    group_text = " / ".join(group_labels)
    value_text = " / ".join(value_labels)

    elements.append(Paragraph(f"対象期間：{start_date} 〜 {end_date}", normal_style))
    elements.append(Paragraph(f"集計項目：{group_text}", normal_style))
    elements.append(Paragraph(f"集計数値：{value_text}", normal_style))
    elements.append(Spacer(1, 16))

    table_data = [list(summary_df.columns)]

    for _, row in summary_df.iterrows():
        table_data.append([str(value) for value in row.values])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", bbox_inches="tight")
    image_buffer.seek(0)

    chart_image = Image(image_buffer, width=450, height=280)
    elements.append(chart_image)

    doc.build(elements)

    pdf_buffer.seek(0)
    return pdf_buffer


# =========================
# Streamlit画面
# =========================
st.title("CSVレポート自動作成デモ")

# st.write(
#     "このツールは、CSVデータの集計・グラフ化・PDF出力を自動化するツールです。"
# )

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    df["date"] = pd.to_datetime(df["date"])

    display_df = df.rename(columns=COLUMN_LABELS)

    st.subheader("読み込んだデータ")
    st.dataframe(display_df)

    start_date = st.date_input("開始日", df["date"].min())
    end_date = st.date_input("終了日", df["date"].max())

    selected_group_labels = st.multiselect(
        "集計する項目を選んでください",
        list(GROUP_OPTIONS.keys()),
        default=["担当者別"]
    )

    selected_value_labels = st.multiselect(
        "集計する数値を選んでください",
        list(VALUE_OPTIONS.keys()),
        default=["売上"]
    )

    if len(selected_group_labels) == 0:
        st.warning("集計する項目を1つ以上選んでください。")
        st.stop()

    if len(selected_value_labels) == 0:
        st.warning("集計する数値を1つ以上選んでください。")
        st.stop()

    group_columns = [GROUP_OPTIONS[label] for label in selected_group_labels]
    value_columns = [VALUE_OPTIONS[label] for label in selected_value_labels]

    filtered_df = df[
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date))
    ]

    summary_df = (
        filtered_df
        .groupby(group_columns)[value_columns]
        .sum()
        .reset_index()
    )

    sort_column = value_columns[0]
    summary_df = summary_df.sort_values(by=sort_column, ascending=False)

    summary_display_df = summary_df.rename(columns=COLUMN_LABELS)

    st.subheader("集計結果")
    st.dataframe(summary_display_df)

    st.subheader("グラフ")

    graph_df = summary_df.copy()

    if len(group_columns) == 1:
        graph_df["集計ラベル"] = graph_df[group_columns[0]].astype(str)
    else:
        graph_df["集計ラベル"] = graph_df[group_columns].astype(str).agg(" / ".join, axis=1)

    fig, ax = plt.subplots(figsize=(10, 5))

    graph_plot_df = graph_df.set_index("集計ラベル")[value_columns]
    graph_plot_df.plot(kind="bar", ax=ax)

    group_title = " × ".join(selected_group_labels)
    value_title = " / ".join(selected_value_labels)

    ax.set_title(f"{group_title}：{value_title}")
    ax.set_xlabel("集計項目")
    ax.set_ylabel("合計値")

    legend_labels = [COLUMN_LABELS[column] for column in value_columns]
    ax.legend(legend_labels)

    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    st.pyplot(fig)

    pdf_file = create_pdf_report(
        summary_df=summary_display_df,
        start_date=start_date,
        end_date=end_date,
        group_labels=selected_group_labels,
        value_labels=selected_value_labels,
        fig=fig
    )

    st.download_button(
        label="PDFレポートをダウンロード",
        data=pdf_file,
        file_name="csv_report_demo.pdf",
        mime="application/pdf"
    )