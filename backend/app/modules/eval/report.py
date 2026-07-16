from __future__ import annotations

import html
import json
from typing import List, Optional

from app.modules.eval.schemas import EvaluationResult


def generate_html_report(result: EvaluationResult, title: Optional[str] = None) -> str:
    report_title = title or ("Evaluation Report \u2014 " + result.run_id[:8])
    agg = result.aggregate_scores
    ragas_metrics = {k: v for k, v in agg.items() if v is not None}
    avg_latency = result.total_latency_ms / max(result.sample_count, 1)

    radar_labels = json.dumps(list(ragas_metrics.keys()) + ["operational"])
    radar_values = json.dumps([round(v * 100, 1) for v in ragas_metrics.values()] + [min(100, max(0, 100 - avg_latency / 10))])

    status_color = "#10b981" if result.status == "completed" else "#ef4444"
    status_label = result.status.upper()

    parts: List[str] = []
    p = parts.append

    p("<!DOCTYPE html>")
    p('<html lang="en">')
    p("<head>")
    p('<meta charset="utf-8">')
    p('<meta name="viewport" content="width=device-width,initial-scale=1">')
    p("<title>" + _esc(report_title) + "</title>")
    p("<style>")
    p("* { margin:0; padding:0; box-sizing:border-box; }")
    p("body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; padding:24px; line-height:1.6; }")
    p(".container { max-width:1200px; margin:0 auto; }")
    p(".header { display:flex; justify-content:space-between; align-items:center; margin-bottom:32px; padding-bottom:16px; border-bottom:1px solid #334155; }")
    p(".header h1 { font-size:1.5rem; color:#f8fafc; }")
    p(".status { padding:4px 12px; border-radius:12px; font-size:.75rem; font-weight:600; background:" + status_color + "20; color:" + status_color + "; border:1px solid " + status_color + "; }")
    p(".grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-bottom:32px; }")
    p(".card { background:#1e293b; border-radius:12px; padding:20px; border:1px solid #334155; }")
    p(".card .label { font-size:.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }")
    p(".card .value { font-size:1.5rem; font-weight:700; color:#f8fafc; }")
    p(".section { margin-bottom:32px; }")
    p(".section h2 { font-size:1.1rem; color:#f8fafc; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #334155; }")
    p(".bars { display:flex; flex-direction:column; gap:12px; }")
    p(".bar-item { display:flex; align-items:center; gap:12px; }")
    p(".bar-label { width:140px; font-size:.85rem; color:#94a3b8; text-align:right; flex-shrink:0; }")
    p(".bar-track { flex:1; height:24px; background:#334155; border-radius:6px; overflow:hidden; }")
    p(".bar-fill { height:100%; border-radius:6px; transition:width .3s; }")
    p(".bar-value { width:60px; font-size:.85rem; font-weight:600; color:#f8fafc; }")
    p("table { width:100%; border-collapse:collapse; font-size:.85rem; }")
    p("th { background:#1e293b; color:#94a3b8; padding:10px 12px; text-align:left; border-bottom:2px solid #334155; position:sticky; top:0; font-weight:600; text-transform:uppercase; font-size:.7rem; letter-spacing:.05em; }")
    p("td { padding:10px 12px; border-bottom:1px solid #1e293b; }")
    p("tr:hover { background:rgba(30,41,59,0.5); }")
    p(".query { max-width:200px; color:#94a3b8; font-size:.8rem; }")
    p(".answer { max-width:250px; font-size:.8rem; color:#cbd5e1; }")
    p(".meta { color:#64748b; font-size:.8rem; }")
    p(".metric-col { min-width:100px; text-align:center; }")
    p(".table-wrapper { overflow-x:auto; background:#1e293b; border-radius:12px; border:1px solid #334155; }")
    p(".agg-row td { background:#1e293b; border-top:2px solid #475569; font-weight:600; }")
    p("</style>")
    p("</head>")
    p("<body>")
    p('<div class="container">')

    # Header
    p('<div class="header">')
    p("<h1>" + _esc(report_title) + "</h1>")
    p('<span class="status">' + status_label + "</span>")
    p("</div>")

    # Summary cards
    p('<div class="grid">')
    p(_card("Samples", str(result.sample_count)))
    p(_card("Avg Latency", "{:.0f}ms".format(avg_latency)))
    p(_card("Total Tokens", "{:,}".format(result.total_tokens.total_tokens)))
    p(_card("Total Cost", "${:.6f}".format(result.total_cost_usd)))
    p(_card("Prompt Tokens", "{:,}".format(result.total_tokens.prompt_tokens)))
    p(_card("Completion Tokens", "{:,}".format(result.total_tokens.completion_tokens)))
    p("</div>")

    # Quality bars
    p('<div class="section"><h2>Ragas Quality Scores</h2><div class="bars">')
    for name, val in ragas_metrics.items():
        pct = val * 100
        color = "#10b981" if val >= 0.7 else "#f59e0b" if val >= 0.4 else "#ef4444"
        p('<div class="bar-item">')
        p('<div class="bar-label">' + _esc(name) + "</div>")
        p('<div class="bar-track"><div class="bar-fill" style="width:{:.1f}%;background:{}"></div></div>'.format(pct, color))
        p('<div class="bar-value">{:.3f}</div>'.format(val))
        p("</div>")
    p("</div></div>")

    # Detailed table
    p('<div class="section"><h2>Detailed Results</h2><div class="table-wrapper"><table>')
    p("<thead><tr><th>#</th><th>Query</th><th>Answer</th>")
    for name in ragas_metrics.keys():
        p('<th class="metric-col">' + _esc(name) + "</th>")
    for name in ["latency", "token_usage", "cost"]:
        p('<th class="metric-col">' + _esc(name) + "</th>")
    p("<th>Latency</th><th>Tokens</th><th>Cost</th></tr></thead>")

    p("<tbody>")
    for sr in result.sample_results:
        p("<tr>")
        p("<td>" + str(sr.sample_index + 1) + "</td>")
        p('<td class="query">' + _esc(sr.query[:80]) + ("..." if len(sr.query) > 80 else "") + "</td>")
        p('<td class="answer">' + _esc(sr.answer[:120]) + ("..." if len(sr.answer) > 120 else "") + "</td>")
        for ms in sr.metric_scores:
            if ms.score is not None:
                color = "#10b981" if ms.score >= 0.7 else "#f59e0b" if ms.score >= 0.4 else "#ef4444"
                p('<td style="color:{};font-weight:600">{:.3f}</td>'.format(color, ms.score))
            else:
                p('<td class="meta">' + _esc(str(ms.reason or "\u2014")) + "</td>")
        p('<td class="meta">{:.0f}ms</td>'.format(sr.latency_ms or 0))
        p('<td class="meta">{:,}</td>'.format(sr.token_usage.total_tokens if sr.token_usage else 0))
        p('<td class="meta">{}</td>'.format("${:.6f}".format(sr.cost_usd) if sr.cost_usd else "\u2014"))
        p("</tr>")

    # Aggregate row
    p('<tr class="agg-row"><td colspan="3"><strong>Aggregate</strong></td>')
    for name, val in ragas_metrics.items():
        color = "#10b981" if val >= 0.7 else "#f59e0b" if val >= 0.4 else "#ef4444"
        p('<td style="color:{};font-weight:700;font-size:1.1em">{:.3f}</td>'.format(color, val))
    p('<td class="meta">{:.0f}ms</td>'.format(avg_latency))
    p('<td class="meta">{:,}</td>'.format(result.total_tokens.total_tokens))
    p('<td class="meta">${:.6f}</td>'.format(result.total_cost_usd))
    p("</tr>")

    p("</tbody></table></div></div>")

    # Footer
    p('<div class="section" style="text-align:center;color:#475569;font-size:.75rem;margin-top:40px">')
    p("Generated by Enterprise RAG Platform Evaluation Module &middot; Run ID: " + _esc(result.run_id))
    p("</div>")
    p("</div>")

    # Radar chart canvas (hidden)
    p('<canvas id="radarChart" width="400" height="400" style="display:none"></canvas>')
    p(_radar_js(radar_labels, radar_values))

    p("</body>")
    p("</html>")

    return "\n".join(parts)


def _esc(text: str) -> str:
    return html.escape(str(text))


def _card(label: str, value: str) -> str:
    return '<div class="card"><div class="label">{}</div><div class="value">{}</div></div>'.format(_esc(label), _esc(value))


def _radar_js(labels_json: str, values_json: str) -> str:
    js = """<script>
(function() {
    var canvas = document.getElementById('radarChart');
    var ctx = canvas.getContext('2d');
    var labels = """ + labels_json + """;
    var values = """ + values_json + """;
    var n = labels.length;
    var cx = 200, cy = 200, r = 150;
    var angleStep = (2 * Math.PI) / n;
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, 400, 400);
    for (var ring = 1; ring <= 4; ring++) {
        ctx.beginPath();
        var rr = (r * ring) / 4;
        for (var i = 0; i <= n; i++) {
            var angle = i * angleStep - Math.PI / 2;
            var x = cx + rr * Math.cos(angle);
            var y = cy + rr * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = '#334155'; ctx.lineWidth = 1; ctx.stroke();
    }
    for (var i = 0; i < n; i++) {
        var angle = i * angleStep - Math.PI / 2;
        ctx.beginPath(); ctx.moveTo(cx, cy);
        ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
        ctx.strokeStyle = '#334155'; ctx.stroke();
    }
    ctx.beginPath();
    for (var i = 0; i <= n; i++) {
        var idx = i % n;
        var angle = idx * angleStep - Math.PI / 2;
        var val = values[idx] / 100;
        var x = cx + r * val * Math.cos(angle);
        var y = cy + r * val * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.fillStyle = 'rgba(59,130,246,0.2)'; ctx.fill();
    ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2; ctx.stroke();
    for (var i = 0; i < n; i++) {
        var angle = i * angleStep - Math.PI / 2;
        var x = cx + r * Math.cos(angle);
        var y = cy + r * Math.sin(angle);
        ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#3b82f6'; ctx.fill();
        ctx.fillStyle = '#94a3b8'; ctx.font = '11px sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(labels[i], cx + (r + 20) * Math.cos(angle), cy + (r + 20) * Math.sin(angle));
    }
})();
</script>"""
    return js
