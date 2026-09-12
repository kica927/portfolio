"""
데스크탑 벤치마크 대시보드 — Intel Arc B580 + Core Ultra 5 225(NPU 내장)에서 진행한
세 트랙(엣지 AI 추론, 자율주행 인지모델, 로보틱스 정책 비교)의 실측 결과를 한 화면에서 본다.

실행: streamlit run app.py
데이터: data.json (포트폴리오 문서의 실측치를 그대로 옮긴 것 — 여기서 새로 측정하지 않음)
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).parent / "data.json"

st.set_page_config(page_title="Desktop Benchmark Dashboard", page_icon="🖥️", layout="wide")


@st.cache_data
def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


data = load_data()
meta = data["meta"]

st.title("🖥️ Desktop Benchmark Dashboard")
st.caption(
    f"{meta['host']} · {meta['cpu']} · {meta['gpu']} · {meta['os']} "
    f"— 실측일 {meta['generated']}"
)

tab_edge, tab_perception, tab_policy = st.tabs(
    ["⚡ 엣지 AI 추론 (A1)", "🚗 자율주행 인지모델 (BDD100K)", "🤖 로보틱스 정책 비교 (ACT vs SmolVLA)"]
)

# ── Tab 1: 엣지 AI 추론 벤치마크 ────────────────────────────────────────────
with tab_edge:
    edge = data["edge_ai"]
    st.subheader(edge["model"])

    df = pd.DataFrame(edge["devices"])
    df_long = df.melt(
        id_vars="device", value_vars=["fp32_fps", "int8_fps"],
        var_name="정밀도", value_name="fps"
    )
    df_long["정밀도"] = df_long["정밀도"].map({"fp32_fps": "원본 IR", "int8_fps": "INT8 IR"})

    col1, col2 = st.columns([3, 2])
    with col1:
        fig = px.bar(
            df_long, x="device", y="fps", color="정밀도", barmode="group",
            title="디바이스별 추론 속도 (fps, 모델 단독 지연 기준)",
            log_y=True,
        )
        fig.update_layout(xaxis_title="", legend_title="")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**INT8 배속(원본 IR 대비)**")
        speed_df = df[["device", "speedup"]].sort_values("speedup", ascending=False)
        fig2 = px.bar(
            speed_df, x="speedup", y="device", orientation="h",
            color="speedup", color_continuous_scale=["#d62728", "#999", "#2ca02c"],
            range_color=[0.7, 2.5],
        )
        fig2.add_vline(x=1.0, line_dash="dash", line_color="gray")
        fig2.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="배속(×)")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("1.0 미만 = INT8이 오히려 느려짐. NPU·맥 CPU 둘 다 반례.")

    acc = edge["accuracy"]
    st.markdown("**정확도·크기 (FP32 IR vs INT8 IR)**")
    m1, m2, m3 = st.columns(3)
    m1.metric("모델 크기", f"{acc['int8_size_mb']} MB", f"-{100*(1-acc['int8_size_mb']/acc['fp32_size_mb']):.0f}%")
    m2.metric("mAP50-95", f"{acc['int8_map50_95']:.4f}", f"{acc['int8_map50_95']-acc['fp32_map50_95']:+.4f}")
    m3.metric("mAP50", f"{acc['int8_map50']:.4f}", f"{acc['int8_map50']-acc['fp32_map50']:+.4f}")

    st.info(
        "**핵심 발견**: \"INT8=항상 빠름\"은 틀렸다. Intel CPU(VNNI)에선 2.3배 가속되지만, "
        "Arc B580(이미 포화)·NPU(FP16 고정이라 dequantize 오버헤드만 얹음)·맥 arm64 CPU(정수 "
        "가속 없음)에서는 INT8이 오히려 느리거나 무의미하다. INT8 이득은 타깃 하드웨어에 종속된다."
    )

# ── Tab 2: 자율주행 인지모델 ────────────────────────────────────────────────
with tab_perception:
    perc = data["perception"]
    before, after = perc["before"], perc["after"]
    st.subheader(perc["model"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("mAP50", f"{after['map50']:.3f}", f"{after['map50']-before['map50']:+.3f} ({after['map50']/before['map50']:.1f}배)")
    m2.metric("mAP50-95", f"{after['map50_95']:.3f}", f"{after['map50_95']-before['map50_95']:+.3f}")
    m3.metric("Recall", f"{after['recall']:.3f}", f"{after['recall']-before['recall']:+.3f} ({after['recall']/before['recall']:.1f}배)")
    m4.metric("Precision", f"{after['precision']:.3f}", f"{after['precision']-before['precision']:+.3f}")

    st.caption(f"Before: {before['label']}, {before['train_minutes']}분 학습 · After: {after['label']}, {after['train_minutes']}분 학습")

    classes = perc["classes"]
    cls_df = pd.DataFrame({
        "class": classes,
        "Before (무작위 1,000장)": [before["per_class_map50"][c] for c in classes],
        "After (균형 3,000장)": [after["per_class_map50"][c] for c in classes],
        "instances(before)": [before["per_class_instances"][c] for c in classes],
    }).sort_values("instances(before)")

    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.bar(
            cls_df.melt(id_vars="class", value_vars=["Before (무작위 1,000장)", "After (균형 3,000장)"],
                        var_name="샘플링", value_name="mAP50"),
            x="class", y="mAP50", color="샘플링", barmode="group",
            title="클래스별 mAP50 — Before / After",
        )
        fig3.update_layout(xaxis_title="", legend_title="")
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        fig4 = px.bar(
            cls_df, x="class", y="instances(before)",
            title="클래스별 학습 인스턴스 수 (Before, 1,000장 기준, 로그축)",
            log_y=True,
        )
        fig4.update_layout(xaxis_title="", yaxis_title="인스턴스 수")
        st.plotly_chart(fig4, use_container_width=True)

    st.warning(
        "**train 클래스는 오버샘플링으로도 못 고쳤다.** 3,000장까지 늘려도 원본 데이터셋(BDD100K "
        "validation split 미러) 안에 기차 인스턴스가 15개뿐이라 mAP50이 여전히 0.0이다 — "
        "재샘플링으로 풀리는 문제와 안 풀리는 문제를 구분해야 한다."
    )

    carla = perc["carla"]
    st.markdown("**CARLA 시뮬레이터 — 헤드리스 구동 검증**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("다운로드", f"{carla['download_gb']} GB", f"{carla['download_sec']}초")
    c2.metric("압축 해제", f"{carla['extracted_gb']} GB")
    c3.metric("헤드리스 기동", carla["headless_boot"])
    c4.metric("인지모델 연결", f"{carla['frames_with_detection']}/{carla['captured_frames']} 프레임 검출")

# ── Tab 3: 로보틱스 정책 비교 ────────────────────────────────────────────────
with tab_policy:
    pol = data["policies"]
    act, smolvla = pol["act"], pol["smolvla"]

    st.subheader("ACT vs SmolVLA — 같은 데이터(kica927/redball)로 학습한 두 정책")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**추론 지연 (XPU, 단일 관측 → 액션)**")
        lat_df = pd.DataFrame({
            "policy": ["ACT", "SmolVLA"],
            "latency_ms": [act["latency_ms_mean"], smolvla["latency_ms_mean"]],
        })
        fig5 = px.bar(lat_df, x="policy", y="latency_ms", color="policy",
                      text_auto=".2f", title=f"SmolVLA가 ACT보다 {smolvla['latency_ms_mean']/act['latency_ms_mean']:.0f}배 느림")
        fig5.update_layout(showlegend=False, xaxis_title="", yaxis_title="지연 (ms)")
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.markdown("**파라미터 수**")
        param_df = pd.DataFrame({
            "policy": ["ACT", "SmolVLA(학습가능)", "SmolVLA(전체)"],
            "params_m": [act["params_total"]/1e6, smolvla["params_trainable"]/1e6, smolvla["params_total"]/1e6],
        })
        fig6 = px.bar(param_df, x="policy", y="params_m", color="policy",
                      text_auto=".1f", title="파라미터 수 (백만 개)")
        fig6.update_layout(showlegend=False, xaxis_title="", yaxis_title="파라미터 (M)")
        st.plotly_chart(fig6, use_container_width=True)

    st.markdown("**Loss 수렴 곡선** (서로 다른 손실 구성 — 절대값 비교 불가, 궤적 형태만 참고)")
    fig7 = go.Figure()
    act_x = [s for s, _ in act["loss_curve"]]
    act_y = [l for _, l in act["loss_curve"]]
    smol_x = [s for s, _ in smolvla["loss_curve"]]
    smol_y = [l for _, l in smolvla["loss_curve"]]
    fig7.add_trace(go.Scatter(x=act_x, y=act_y, mode="lines+markers", name="ACT (20,000 step)"))
    fig7.add_trace(go.Scatter(x=smol_x, y=smol_y, mode="lines+markers", name="SmolVLA (6,000 step)"))
    fig7.update_layout(xaxis_title="학습 step", yaxis_title="loss", legend_title="")
    st.plotly_chart(fig7, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("체크포인트 크기", f"ACT {act['checkpoint_mb']}MB / SmolVLA {smolvla['checkpoint_mb']}MB",
               f"{smolvla['checkpoint_mb']/act['checkpoint_mb']:.1f}배")
    m2.metric("학습 시간", f"ACT {act['train_minutes']:.0f}분 / SmolVLA {smolvla['train_minutes']:.0f}분")
    m3.metric("학습 스텝", f"ACT {act['steps']:,} / SmolVLA {smolvla['steps']:,}")

    ov = smolvla["openvino_attempt"]
    st.error(
        f"**SmolVLA 경량화 시도는 미해결.** OpenVINO ONNX export는 예상외로 성공했지만, "
        f"CPU 지연이 {ov['cpu_latency_ms']:.0f}ms로 오히려 4배+ 느려졌고 GPU 컴파일은 실패했다. "
        f"출력값을 원본 PyTorch와 대조하지 않아 결과 정합성도 검증되지 않았다 — 경량화 이득은 "
        f"아직 얻지 못했다."
    )

    st.caption(
        "스텝 수가 다름(ACT 20,000 vs SmolVLA 6,000)을 감안해야 하는 비교다. "
        "실기 성공률 비교는 하드웨어 접근 종료로 여전히 불가능 — 이 비교는 학습 비용·추론 "
        "지연이라는 간접 지표에 한정된다."
    )

st.divider()
st.caption(
    "데이터 출처: `projects/a1-edge-opt.md` · `projects/edge-perception-desktop.md` · "
    "`projects/act-vs-smolvla-offline.md` (같은 저장소). 이 앱은 새로 측정하지 않고 "
    "기존 실측 결과를 시각화만 한다."
)
