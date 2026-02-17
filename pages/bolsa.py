from rgbmatrix import graphics
import config as cfg
import utils
import data

def draw(canv):
    st = data.dados['stocks']
    
    # Layout Tabela Limpa
    # Colunas: [Nome]   [Valor]    [%]
    # X aprox: 1        22         48
    
    # 1. IBOVESPA (Brasil)
    y = 15
    graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_BLUE, "IBOV")
    graphics.DrawText(canv, cfg.font_s, 22, y, cfg.C_WHITE, f"{st['ibov']/1000:.0f}k")
    cor = cfg.C_GREEN if st['ibov_var'] >= 0 else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, 42, y, cor, f"{st['ibov_var']:+.1f}%")

    # 2. S&P 500 (EUA Geral)
    y += 10
    graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_WHITE, "S&P")
    graphics.DrawText(canv, cfg.font_s, 22, y, cfg.C_WHITE, f"{st['sp500']:.0f}")
    cor = cfg.C_GREEN if st['sp500_var'] >= 0 else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, 42, y, cor, f"{st['sp500_var']:+.1f}%")

    # 3. NASDAQ (Tecnologia)
    y += 10
    graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_ORANGE, "NDX")
    graphics.DrawText(canv, cfg.font_s, 22, y, cfg.C_WHITE, f"{st['nasdaq']/1000:.0f}k")
    cor = cfg.C_GREEN if st['nasdaq_var'] >= 0 else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, 42, y, cor, f"{st['nasdaq_var']:+.1f}%")

    # 4. Dólar (USD)
    y += 10
    usd_val = data.dados['usdtbrl']
    graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_GREEN, "USD")
    # Formatação com R$ e vírgula
    graphics.DrawText(canv, cfg.font_s, 22, y, cfg.C_WHITE, f"R${usd_val:.2f}".replace(".", ","))
