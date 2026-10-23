# -*- coding: utf-8 -*-
import re

with open(r"C:\Users\User\Desktop\iabox\static\index.html", "r", encoding="utf-8") as f:
    html = f.read()

print("--- AUDITORIA DE REGRAS ANTI-VIBE CODE ---")

# 1. Favicon
has_favicon = bool(re.search(r'rel=["\'](?:shortcut )?icon["\']', html, re.I))
print(f"1. Favicon presente: {has_favicon}")

# 2. Travessoes (—)
em_dashes = len(re.findall(r"\u2014", html))
print(f"2. Travessoes (\u2014) encontrados: {em_dashes}")

# 3. Gradientes e elementos roxo/fuchsia
purple_matches = len(re.findall(r"purple|fuchsia", html, re.I))
print(f"3. Ocorrencias de purple/fuchsia: {purple_matches}")

# 4. Botoes pilula (rounded-full em botoes)
pill_buttons = len(re.findall(r"<button[^>]*class=[\"'][^\"']*rounded-full", html, re.I))
print(f"4. Botoes rounded-full: {pill_buttons}")

# 5. Avaliacoes / Depoimentos falsos
has_reviews = bool(re.search(r"depoimento|avalia[çc][õo]es|estrelas|5\s*estrelas|o que dizem", html, re.I))
print(f"5. Seção de depoimentos/avaliações presente: {has_reviews}")

# 6. Metricas / Contadores falsos
has_fake_stats = re.findall(r"(?:10\.000\+|500k|99\.9%|clientes satisfeitos|avaliação média)", html, re.I)
print(f"6. Métricas suspeitas encontradas: {has_fake_stats}")

# 7. Animacao de cursor
has_cursor = bool(re.search(r"cursor-trail|custom-cursor|cursor-dot|cursor-follower", html, re.I))
print(f"7. Animação de cursor: {has_cursor}")

# 8. Selo 'feito com IA' ou similar
ai_badges = re.findall(r"(?:feito com ia|criado com ia|gerado por ia|powered by ai|vibe code|built with)", html, re.I)
print(f"8. Selos 'Feito com IA': {ai_badges}")

# 9. Politica de Privacidade
has_privacy = "política de privacidade" in html.lower() or "politica de privacidade" in html.lower()
print(f"9. Política de Privacidade presente: {has_privacy}")

# 10. Termos e Condicoes
has_terms = "termos de uso" in html.lower() or "termos e condições" in html.lower() or "termos de serviço" in html.lower()
print(f"10. Termos de Serviço presente: {has_terms}")

# 11. Headline / Topo vago
hero_matches = re.findall(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
if hero_matches:
    print(f"11. Headline H1 atual: {hero_matches[0].strip()[:100]}")
