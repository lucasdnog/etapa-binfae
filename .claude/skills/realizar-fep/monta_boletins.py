"""Monta, para cada militar com Parte de Etapa no mês, um PDF com os boletins diários dos dias em que ele tirou serviço.

Uso:  python -I monta_boletins.py MÊS [pasta_dos_dados]      (ex.: outubro, "novembro 2026")

Entrada:  <pasta>/ETAPAS EVENTUAIS - MÊS/*.pdf  e  <pasta>/BOLETIM/<MÊS AAAA>/DD.MM.pdf (boletim do próprio dia do serviço)
Saída:    <pasta>/BOLETIM/BOLETINS POR MILITAR - <MÊS AAAA>/Boletim - NOME - SARAM.pdf  +  situacao.json
Permuta:  militar cujo SARAM não aparece em "SENTINELAS DE JACAREPAGUÁ" em nenhum dos seus dias -> sem boletim (o FEP vai só com etapa e ficha).
"""
import sys, os, re, json, glob, unicodedata
import pymupdf

_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.local.json")
PASTA_PADRAO = json.load(open(_CFG, encoding="utf-8")).get("pasta_dados", "") if os.path.exists(_CFG) else ""
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().upper()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pasta = sys.argv[2] if len(sys.argv) > 2 else PASTA_PADRAO
    mi = [i for i, n in enumerate(MESES) if norm(n) in norm(sys.argv[1])]
    if not mi:
        raise SystemExit(f"Mês não reconhecido: {sys.argv[1]}")
    mes = mi[0] + 1
    y = re.search(r"\b(20\d\d)\b", sys.argv[1])

    etapas = glob.glob(os.path.join(pasta, f"ETAPAS EVENTUAIS - {norm(MESES[mes - 1])}*", "*.pdf")) + \
        glob.glob(os.path.join(pasta, f"ETAPAS EVENTUAIS - {MESES[mes - 1].upper()}*", "*.pdf"))
    militares = []
    for p in sorted(set(etapas)):
        m = re.search(r"Etapa Eventual - (.+?) - (\d{7})\.pdf$", os.path.basename(p))
        if not m:
            continue
        txt = " ".join(pg.get_text() for pg in pymupdf.open(p))
        ds = sorted({(int(a), int(b), int(c)) for c, b, a in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", txt) if int(b) == mes})
        if ds:
            militares.append({"nome": re.sub(r"^(S[12]|CB|[123]S|SO)\s+\S+\s+", "", m.group(1)), "saram": m.group(2), "ano": ds[0][0], "dias": [d for _, _, d in ds]})
    if not militares:
        raise SystemExit(f"Nenhuma Parte de Etapa de {MESES[mes - 1]} em {pasta}")
    ano = int(y.group(1)) if y else militares[0]["ano"]
    rotulo = f"{MESES[mes - 1].upper()} {ano}"

    dir_bol = next((d for d in glob.glob(os.path.join(pasta, "BOLETIM", "*")) if os.path.isdir(d) and norm(os.path.basename(d)) == norm(rotulo)), None)
    if not dir_bol:
        raise SystemExit(f"Pasta de boletins não encontrada: {os.path.join(pasta, 'BOLETIM', rotulo)}")
    bol, ignorados = {}, []
    for f in os.listdir(dir_bol):
        m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.pdf", f, re.I)
        if not m or int(m.group(2)) != mes:
            if f.lower().endswith(".pdf"):
                ignorados.append(f)
            continue
        d = int(m.group(1))
        t = norm(" ".join(pg.get_text() for pg in pymupdf.open(os.path.join(dir_bol, f))))
        h = re.search(r"PARA O DIA (\d{1,2}) DE ([A-Z]+)", t)
        s = re.search(r"SENTINELAS DE JACAREPAGUA\.*:(.*?)(?=\n[^\n]*\.\.:|$)", t, re.S)
        bol[d] = {"arq": os.path.join(dir_bol, f), "cab_ok": bool(h and int(h.group(1)) == d), "sent": re.findall(r"\b\d{7}\b", s.group(1)) if s else []}

    saida = os.path.join(pasta, "BOLETIM", f"BOLETINS POR MILITAR - {rotulo}")
    os.makedirs(saida, exist_ok=True)
    situacao, linhas = {}, []
    for m in militares:
        faltam = [d for d in m["dias"] if d not in bol]
        com_nome = [d for d in m["dias"] if d in bol and m["saram"] in bol[d]["sent"]]
        sem_nome = [d for d in m["dias"] if d in bol and d not in com_nome]
        arq = os.path.join(saida, f"Boletim - {m['nome']} - {m['saram']}.pdf")
        if faltam:
            st = "faltam boletins"
        elif not com_nome:
            st = "permuta"
        else:
            out = pymupdf.open()
            for d in m["dias"]:
                out.insert_pdf(pymupdf.open(bol[d]["arq"]))
            out.save(arq, garbage=3, deflate=True)
            st = "ok" if not sem_nome else "ok (nome ausente em alguns dias)"
        if st != "ok" and not st.startswith("ok") and os.path.exists(arq):
            os.remove(arq)
        situacao[m["saram"]] = {"nome": m["nome"], "situacao": st, "dias": m["dias"], "sem_nome": sem_nome, "faltam": faltam,
                                "arquivo": arq if st.startswith("ok") else None}
        linhas.append(f"{m['nome'][:34]:34} {m['saram']}  {len(m['dias']):2} dias  {st}" + (f"  sem nome em {sem_nome}" if sem_nome and st.startswith("ok") else "")
                      + (f"  faltam {faltam}" if faltam else ""))
    json.dump(situacao, open(os.path.join(saida, "situacao.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Boletins de {rotulo}: {len(bol)} diários" + (f" | ignorados: {ignorados}" if ignorados else "")
          + (f" | cabeçalho com outro dia: {[d for d, b in bol.items() if not b['cab_ok']]}" if any(not b['cab_ok'] for b in bol.values()) else ""))
    print("\n".join(linhas))
    print(f"\nSaída: {saida}")


if __name__ == "__main__":
    main()
