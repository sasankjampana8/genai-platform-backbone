import html

from shared.config import settings
from shared.ids import generate_artifact_id
from shared.s3_service import create_presigned_get, put_text


def _svg_bar_chart(payload: dict) -> str:
    data = payload.get("data") or []
    title = html.escape(payload.get("title") or "Chart")
    width = 720
    height = 420
    margin = 56
    values = [float(item.get("value", 0)) for item in data] or [1]
    max_value = max(values) or 1
    bar_gap = 14
    bar_width = max(18, (width - (2 * margin) - (bar_gap * max(len(data) - 1, 0))) / max(len(data), 1))
    bars = []
    for index, item in enumerate(data):
        value = float(item.get("value", 0))
        label = html.escape(str(item.get("label", f"Item {index + 1}")))
        bar_height = (height - 150) * (value / max_value)
        x = margin + index * (bar_width + bar_gap)
        y = height - margin - bar_height
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#5b8def" rx="4"/>'
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 28}" text-anchor="middle" font-size="13" fill="#d7d7d7">{label}</text>'
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="13" fill="#ffffff">{value:g}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#111111"/>'
        f'<text x="{margin}" y="38" font-size="24" font-family="Arial" font-weight="700" fill="#ffffff">{title}</text>'
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#555"/>'
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#555"/>'
        + "".join(bars)
        + "</svg>"
    )


def create_chart_artifact(user_id: str, run_id: str, payload: dict) -> dict:
    artifact_id = generate_artifact_id()
    chart_payload = payload or {
        "title": "CloudRAG Generated Chart",
        "data": [{"label": "No data", "value": 1}],
    }
    svg = _svg_bar_chart(chart_payload)
    s3_key = f"artifacts/{user_id}/{run_id}/{artifact_id}.svg"
    put_text(settings.RAW_BUCKET, s3_key, svg, content_type="image/svg+xml")
    return {
        "artifact_id": artifact_id,
        "artifact_type": "chart",
        "content_type": "image/svg+xml",
        "s3_key": s3_key,
        "presigned_url": create_presigned_get(settings.RAW_BUCKET, s3_key),
    }
