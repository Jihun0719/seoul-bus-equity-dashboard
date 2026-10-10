"""E 담당: 자치구별 버스 인프라 지도와 선택 자치구 정류소 표시."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from shapely.geometry import mapping
"""express사용을 위한 호출"""
import plotly.express as px

class Visualizer:
    """C 담당 객체 및 D 담당 계산 메서드를 활용하는 지도 시각화 클래스."""

    METRICS = {
        "equity_score": ("종합 형평성 점수", "점"),
        "stop_density": ("면적당 정류소 수", "개/㎢"),
        "stops_per_population": ("생활인구 1만 명당 정류소 수", "개/1만 명"),
    }
    # 낮은 값은 밝은 주황, 높은 값은 진한 파랑으로 구별합니다.
    COLORSCALE = [
        [0.00, "#fff0c2"],
        [0.20, "#f9b66d"],
        [0.40, "#ed765e"],
        [0.60, "#9a65ac"],
        [0.80, "#426ab3"],
        [1.00, "#173a75"],
    ]

    def __init__(self, districts: Mapping[str, Any], bus_stops: Sequence[Any]):
        if not districts:
            raise ValueError("자치구 객체가 비어 있습니다.")
        self.districts = districts
        self.bus_stops = bus_stops

    def prepare_map_data(self) -> pd.DataFrame:
        """지도와 향후 F 담당 차트에서 공통으로 사용하는 지표 표."""
        items = list(self.districts.values())
        densities = [d.calculate_stop_density() for d in items]
        per_population = [d.calculate_stops_per_population() for d in items]
        d_min, d_max = min(densities), max(densities)
        p_min, p_max = min(per_population), max(per_population)
        rows = []
        for d, den, pop in zip(items, densities, per_population):
            if d.geometry is None or d.geometry.is_empty:
                raise ValueError(f"{d.district_name}: 지도 경계가 없습니다.")
            rows.append({
                "district_code": d.district_code,
                "district_name": d.district_name,
                "geometry": d.geometry,
                "area_km2": d.area,
                "living_population": d.living_population,
                "bus_stop_count": d.bus_stop_count,
                "population_date": d.population_date,
                "stop_density": den,
                "stops_per_population": pop,
                "equity_score": d.calculate_equity_score(d_min, d_max, p_min, p_max),
            })
        return pd.DataFrame(rows).sort_values("district_code").reset_index(drop=True)

    def create_map(
        self,
        metric: str = "equity_score",
        show_bus_stops: bool = False,
        selected_district_code: str | None = None,
    ) -> go.Figure:
        """지도 생성. 선택 자치구가 있으면 해당 구로 확대하고 정류소를 제한합니다."""
        if metric not in self.METRICS:
            raise ValueError(f"지원하지 않는 지표: {metric}")
        df = self.prepare_map_data()
        if selected_district_code is not None:
            selected_district_code = str(selected_district_code)
            if selected_district_code not in set(df["district_code"]):
                raise ValueError(f"존재하지 않는 자치구 코드: {selected_district_code}")

        label, unit = self.METRICS[metric]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"district_code": row.district_code},
                    "geometry": mapping(row.geometry),
                }
                for row in df.itertuples(index=False)
            ],
        }
        customdata = df[[
            "district_name", "bus_stop_count", "stop_density",
            "stops_per_population", "equity_score",
        ]].to_numpy()
        fig = go.Figure(go.Choropleth(
            geojson=geojson,
            locations=df["district_code"],
            featureidkey="properties.district_code",
            z=df[metric],
            zmin=0 if metric == "equity_score" else float(df[metric].min()),
            zmax=100 if metric == "equity_score" else float(df[metric].max()),
            colorscale=self.COLORSCALE,
            marker_line_color="#ffffff",
            marker_line_width=1.2,
            colorbar=dict(title=unit, thickness=17, len=0.76),
            customdata=customdata,
            selectedpoints=None,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "정류소: %{customdata[1]:,.0f}개<br>"
                "면적당 정류소: %{customdata[2]:.2f}개/㎢<br>"
                "생활인구 1만 명당: %{customdata[3]:.2f}개<br>"
                "종합 점수: %{customdata[4]:.1f}점"
                "<extra></extra>"
            ),
        ))

        if show_bus_stops:
            stops = self.bus_stops
            if selected_district_code is not None:
                stops = [s for s in stops if s.district_code == selected_district_code]
            if stops:
                fig.add_trace(go.Scattergeo(
                    lon=[s.longitude for s in stops],
                    lat=[s.latitude for s in stops],
                    text=[f"{s.stop_name} ({s.stop_id})" for s in stops],
                    mode="markers",
                    marker=dict(size=5 if selected_district_code else 2.5,
                                color="#ec3c34", opacity=0.85 if selected_district_code else 0.5,
                                line=dict(width=0.5 if selected_district_code else 0, color="white")),
                    name="버스정류소",
                    hovertemplate="%{text}<extra>버스정류소</extra>",
                ))

        if selected_district_code is None:
            fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
        else:
            geometry = df.loc[df["district_code"] == selected_district_code, "geometry"].iloc[0]
            minx, miny, maxx, maxy = geometry.bounds
            # 경계 밖 여백 12%를 추가해 확대된 지도가 잘리지 않게 합니다.
            padx = max((maxx - minx) * 0.12, 0.006)
            pady = max((maxy - miny) * 0.12, 0.006)
            fig.update_geos(
                visible=False,
                projection_type="mercator",
                lonaxis_range=[minx - padx, maxx + padx],
                lataxis_range=[miny - pady, maxy + pady],
            )

        selected_name = ""
        if selected_district_code is not None:
            selected_name = df.loc[df["district_code"] == selected_district_code, "district_name"].iloc[0]
        fig.update_layout(
            title=f"{selected_name or '서울시 자치구별'} {label}",
            margin=dict(l=0, r=0, t=55, b=0),
            height=680,
            paper_bgcolor="rgba(0,0,0,0)",
            clickmode="event+select",
            uirevision=f"{metric}-{selected_district_code or 'seoul'}",
        )
        return fig

# ==================== F 담당 영역 (차트 시각화) ====================
    def create_bar_chart(self, selected_district_code: str | None = None) -> go.Figure:
        """
        F-1: 자치구별 종합 형평성 점수 막대그래프
        selected_district_code가 전달되면 해당 자치구의 막대 색상을 파란색으로 강조합니다.
        """
        df = self.prepare_map_data().sort_values("equity_score", ascending=True)

        if selected_district_code is not None:
            selected_district_code = str(selected_district_code)

        # 선택된 자치구 강조 색상 (선택 구: 파란색, 나머지: 회색)
        colors = [
            "#173a75" if str(code) == selected_district_code else "#CBD5E1"
            for code in df["district_code"]
        ]

        fig = go.Figure(
            go.Bar(
                x=df["equity_score"],
                y=df["district_name"],
                orientation="h",
                marker_color=colors,
                hovertemplate="<b>%{y}</b><br>형평성 점수: %{x:.1f}점<extra></extra>",
            )
        )

        fig.update_layout(
            title="자치구별 종합 형평성 점수 비교",
            xaxis_title="형평성 점수 (점)",
            yaxis_title="자치구",
            template="plotly_white",
            height=450,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        return fig

    def create_scatter_plot(self, selected_district_code: str | None = None) -> go.Figure:
        """
        F-2: 인구수 대비 버스 정류소 수 관계 산점도 및 추세선
        - 별도의 별표 강조 마커나 범례 없이 전체 분포 및 추세선을 깔끔하게 표시합니다.
        """
        df = self.prepare_map_data()

        # 전체 자치구 기본 산점도 및 OLS 추세선 생성
        fig = px.scatter(
            df,
            x="living_population",
            y="bus_stop_count",
            hover_name="district_name",
            text="district_name",
            title="인구수 대비 버스 정류소 수 관계",
            labels={
                "living_population": "생활인구 수 (명)",
                "bus_stop_count": "버스 정류소 수 (개)",
            },
            trendline="ols",
        )

        # 모든 점의 스타일을 통일 (강조 마커 제거)
        fig.update_traces(
            textposition="top center",
            marker=dict(size=9, color="#426ab3", opacity=0.85),
            selector=dict(mode="markers+text")
        )

        fig.update_layout(
            template="plotly_white",
            height=500,
            margin=dict(l=10, r=10, t=50, b=10),
            showlegend=False  # 불필요한 강조 범례 제거
        )
        return fig
        # 선택한 자치구 점 강조
        if selected_district_code is not None and selected_district_code in set(df["district_code"]):
            selected_row = df[df["district_code"] == selected_district_code].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[selected_row["living_population"]],
                    y=[selected_row["bus_stop_count"]],
                    mode="markers",
                    marker=dict(size=14, color="#173a75", symbol="star"),
                    name="선택 자치구",
                    hoverinfo="skip",
                )
            )

        fig.update_traces(textposition="top center")
        fig.update_layout(
            template="plotly_white",
            height=450,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        return fig