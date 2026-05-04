from dash import dash_table, dcc, html

from ui.styles import BRANCO, SECTION_STYLE


def card(titulo, valor, cor="#2563eb"):
    return html.Div(
        [
            html.Div(titulo, style={"fontSize": "12px", "color": "#475569", "marginBottom": "6px"}),
            html.Div(valor, style={"fontSize": "24px", "fontWeight": "700", "color": cor}),
        ],
        style={
            "backgroundColor": BRANCO,
            "borderLeft": f"6px solid {cor}",
            "borderRadius": "12px",
            "padding": "14px 16px",
            "flex": "1 1 240px",
            "minWidth": "220px",
            "boxShadow": "0 2px 10px rgba(15,23,42,0.1)",
        },
    )



def box_titulo(titulo, subtitulo=None):
    children = [html.H3(titulo, style={"margin": "0 0 6px 0"})]
    if subtitulo:
        children.append(html.Div(subtitulo, style={"color": "#64748b", "marginBottom": "10px"}))
    return children


def dropdown_filtro(id_comp, titulo, opcoes):
    return html.Div(
        [
            html.Label(titulo, style={"fontWeight": "600", "marginBottom": "6px", "display": "block"}),
            dcc.Dropdown(id=id_comp, options=opcoes, multi=True, placeholder=f"Selecione {titulo.lower()}"),
        ],
        style={"minWidth": "220px", "flex": "1"},
    )


def tabela_padrao(id_tabela, page_size=12):
    return dash_table.DataTable(
        id=id_tabela,
        columns=[],
        data=[],
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        export_format="xlsx",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Arial",
            "fontSize": "13px",
            "maxWidth": "340px",
            "whiteSpace": "normal",
        },
        style_header={"fontWeight": "700", "backgroundColor": "#f3f4f6"},
    )


def secao_filtros(*children):
    return html.Div(list(children), style={**SECTION_STYLE, "display": "flex", "gap": "12px", "flexWrap": "wrap"})


def fig_vazia(titulo="Sem dados para exibir"):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(
        title=titulo,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": titulo, "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "showarrow": False, "font": {"size": 16}}],
        margin=dict(l=10, r=10, t=50, b=10),
        height=480,
    )
    return fig
