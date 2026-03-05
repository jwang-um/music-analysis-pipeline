"""Interactive Plotly visualisations for the desktop UI."""

import math
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict, List, Optional, Tuple

_TAB10 = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

_CLICK_JS = """
<script>
document.addEventListener('click', function(e) {
  var target = e.target;
  if (target && target.dataset && target.dataset.ts) {
    navigator.clipboard.writeText(target.dataset.ts);
  }
});
var plot = document.querySelector('.plotly-graph-div');
if (plot) {
  plot.on('plotly_click', function(data) {
    if (data.points && data.points.length) {
      var pt = data.points[0];
      var txt = pt.customdata || pt.text || '';
      if (txt) navigator.clipboard.writeText(String(txt));
    }
  });
}
</script>
"""


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f'{m:02d}:{s:02d}'


def _mov_at(t: float, mov_times: List[float], mov_names: List[str]) -> str:
    idx = 0
    for i, mt in enumerate(mov_times):
        if t >= mt:
            idx = i
    return mov_names[idx] if idx < len(mov_names) else f'Mov {idx+1}'


def _arc_points(t1: float, t2: float, n_pts: int = 40):
    """Compute parametric semicircle points for an arc."""
    mid = (t1 + t2) / 2
    half_w = abs(t2 - t1) / 2
    height = min(math.sqrt(abs(t2 - t1)) * 0.08, 0.6)
    theta = np.linspace(0, math.pi, n_pts)
    xs = mid + half_w * np.cos(theta)
    ys = height * np.sin(theta)
    return xs, ys


def arc_plot_interactive(
    motif_pairs: List[Tuple[float, float]],
    family_labels: List[int],
    duration_sec: float,
    movement_times_sec: Optional[List[float]] = None,
    movement_names: Optional[List[str]] = None,
    cross_part_pairs: Optional[List[Tuple[float, float]]] = None,
    cross_part_details: Optional[List[dict]] = None,
    title: str = '',
) -> str:
    """Return Plotly HTML for an interactive arc plot."""
    fig = go.Figure()

    mov_times = movement_times_sec or []
    mov_names = movement_names or []

    # Within-part arcs grouped by family
    families = set(family_labels) if family_labels else set()
    for fam in sorted(families):
        xs_all, ys_all, hovers = [], [], []
        for idx, ((t1, t2), label) in enumerate(zip(motif_pairs, family_labels)):
            if label != fam:
                continue
            xs, ys = _arc_points(t1, t2)
            xs_all.extend(xs.tolist() + [None])
            ys_all.extend(ys.tolist() + [None])
            m1 = _mov_at(t1, mov_times, mov_names)
            m2 = _mov_at(t2, mov_times, mov_names)
            span = abs(t2 - t1)
            hover = (f'Family {fam}<br>'
                     f'{_fmt(t1)} ({m1}) \u2194 {_fmt(t2)} ({m2})<br>'
                     f'Span: {_fmt(span)}')
            hovers.extend([hover] * 40 + [None])

        fig.add_trace(go.Scatter(
            x=xs_all, y=ys_all, mode='lines',
            line=dict(color=_TAB10[fam % 10], width=1.2),
            opacity=0.7, name=f'Family {fam}',
            hovertext=hovers, hoverinfo='text',
            customdata=[_fmt(motif_pairs[0][0])] if motif_pairs else [],
        ))

    # Cross-part arcs (dashed, separate group)
    if cross_part_pairs and cross_part_details:
        xs_all, ys_all, hovers = [], [], []
        for (t1, t2), detail in zip(cross_part_pairs, cross_part_details):
            xs, ys = _arc_points(t1, t2)
            xs_all.extend(xs.tolist() + [None])
            ys_all.extend(ys.tolist() + [None])
            m1 = _mov_at(t1, mov_times, mov_names)
            m2 = _mov_at(t2, mov_times, mov_names)
            hover = (f'Cross-part<br>'
                     f'{detail["part_a"]} \u2192 {detail["part_b"]}<br>'
                     f'{_fmt(t1)} ({m1}) \u2194 {_fmt(t2)} ({m2})<br>'
                     f'Distance: {detail["distance"]:.2f}')
            hovers.extend([hover] * 40 + [None])

        fig.add_trace(go.Scatter(
            x=xs_all, y=ys_all, mode='lines',
            line=dict(color='#E8590C', width=1.0, dash='dash'),
            opacity=0.55, name='Cross-part',
            hovertext=hovers, hoverinfo='text',
            visible='legendonly',
        ))

    # Movement boundary lines
    for i, t in enumerate(mov_times):
        fig.add_vline(x=t, line_dash='dash', line_color='#333', line_width=1,
                      opacity=0.5)
        if i < len(mov_names):
            fig.add_annotation(x=t + 2, y=0.95, text=mov_names[i],
                               showarrow=False, font=dict(size=10, color='#333'),
                               yref='y')

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(title='Time (seconds)', range=[0, duration_sec]),
        yaxis=dict(range=[-0.03, 1.05], showticklabels=False, title=''),
        height=340,
        margin=dict(l=40, r=20, t=50, b=40),
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        hovermode='closest',
    )

    html = pio.to_html(fig, full_html=True, include_plotlyjs=True)
    return html.replace('</body>', _CLICK_JS + '\n</body>')


def ssm_plot_interactive(
    ssm: np.ndarray,
    boundaries=None,
    movement_frames: Optional[List[int]] = None,
    movement_names: Optional[List[str]] = None,
    section_annotations: Optional[List[dict]] = None,
    title: str = 'Self-Similarity Matrix',
    sr: int = 22050,
    hop_length: int = 512,
    beat_frames: Optional[np.ndarray] = None,
) -> str:
    """Return Plotly HTML for an interactive SSM heatmap."""
    n = ssm.shape[0]

    if beat_frames is not None and len(beat_frames) >= n:
        time_axis = beat_frames[:n].astype(float) * hop_length / sr
    else:
        time_axis = np.arange(n, dtype=float) * hop_length / sr

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=ssm, x=time_axis, y=time_axis,
        colorscale='Magma', showscale=True,
        hovertemplate='X: %{x:.1f}s<br>Y: %{y:.1f}s<br>Similarity: %{z:.3f}<extra></extra>',
    ))

    shapes = []
    annotations = []

    if boundaries is not None:
        for b in boundaries:
            t_b = time_axis[min(b, n - 1)]
            for axis in ['x', 'y']:
                shapes.append(dict(
                    type='line', **{f'{axis}0': t_b, f'{axis}1': t_b},
                    **{f'{"y" if axis == "x" else "x"}0': time_axis[0],
                       f'{"y" if axis == "x" else "x"}1': time_axis[-1]},
                    line=dict(color='cyan', width=0.6, dash='dot'),
                    opacity=0.5,
                ))

    mov_frames = movement_frames or []
    mov_names = movement_names or []
    for i, f in enumerate(mov_frames):
        t_f = time_axis[min(f, n - 1)]
        for axis in ['x', 'y']:
            shapes.append(dict(
                type='line', **{f'{axis}0': t_f, f'{axis}1': t_f},
                **{f'{"y" if axis == "x" else "x"}0': time_axis[0],
                   f'{"y" if axis == "x" else "x"}1': time_axis[-1]},
                line=dict(color='white', width=1.2, dash='dash'),
                opacity=0.8,
            ))
        if i < len(mov_names):
            annotations.append(dict(
                x=t_f + 3, y=t_f + 3, text=mov_names[i],
                showarrow=False, font=dict(size=10, color='white'),
            ))

    if section_annotations:
        for ann in section_annotations:
            mf = ann['mid_frame']
            t_m = time_axis[min(mf, n - 1)]
            annotations.append(dict(
                x=t_m, y=t_m, text=f"<b>{ann['letter']}</b>",
                showarrow=False,
                font=dict(size=11, color='yellow'),
                bgcolor='rgba(0,0,0,0.6)',
                borderpad=3,
            ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(title='Time (s)'),
        yaxis=dict(title='Time (s)', scaleanchor='x'),
        shapes=shapes, annotations=annotations,
        height=650, width=700,
        margin=dict(l=60, r=20, t=50, b=50),
        template='plotly_white',
    )

    html = pio.to_html(fig, full_html=True, include_plotlyjs=True)
    return html.replace('</body>', _CLICK_JS + '\n</body>')


def nmf_plot_interactive(
    H: np.ndarray,
    hop_length: int,
    sr: int,
    movement_times_sec: Optional[List[float]] = None,
    movement_names: Optional[List[str]] = None,
    component_labels: Optional[Dict[int, str]] = None,
    title: str = 'NMF Textures',
) -> str:
    """Return Plotly HTML for an interactive NMF activation heatmap."""
    n_comp, n_frames = H.shape
    times = np.arange(n_frames) * hop_length / sr
    H_display = np.log1p(H)

    y_labels = [component_labels.get(i, f'Comp {i}') if component_labels
                else f'Comp {i}' for i in range(n_comp)]

    hover_template = ('Time: %{x:.1f}s<br>'
                      'Component: %{customdata}<br>'
                      'Activation: %{z:.3f}<extra></extra>')
    customdata = np.array([[y_labels[r]] * n_frames for r in range(n_comp)])

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=H_display, x=times, y=list(range(n_comp)),
        colorscale='Viridis', showscale=True,
        customdata=customdata,
        hovertemplate=hover_template,
    ))

    shapes = []
    annotations = []
    mov_times = movement_times_sec or []
    mov_names = movement_names or []
    for i, t in enumerate(mov_times):
        shapes.append(dict(
            type='line', x0=t, x1=t, y0=-0.5, y1=n_comp - 0.5,
            line=dict(color='white', width=1.2, dash='dash'),
            opacity=0.8,
        ))
        if i < len(mov_names):
            annotations.append(dict(
                x=t + 1, y=n_comp - 0.3, text=mov_names[i],
                showarrow=False, font=dict(size=9, color='white'),
            ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(title='Time (s)'),
        yaxis=dict(
            title='NMF Component',
            tickvals=list(range(n_comp)),
            ticktext=y_labels,
        ),
        shapes=shapes, annotations=annotations,
        height=420,
        margin=dict(l=160, r=20, t=50, b=40),
        template='plotly_white',
    )

    html = pio.to_html(fig, full_html=True, include_plotlyjs=True)
    return html.replace('</body>', _CLICK_JS + '\n</body>')
