"""Prepara um FEP de Etapa Eventual: acha o militar pelo nome de guerra (ou SARAM), lê os dias da Parte de Etapa
e copia os anexos para dentro de ClaudeCode (o navegador só anexa arquivos dessa pasta).

Uso:  python -I fep_dados.py "NOME DE GUERRA ou SARAM" [mês] [pasta_dos_dados]
      mês: nome do mês (ex.: novembro, "novembro 2026"). Sem mês, usa a Parte de Etapa mais recente do militar.
Saída: JSON com militar, lacunas, chefe imediato e caminhos dos anexos. O CPF nunca é impresso.
Dados pessoais (pasta, chefe imediato, legislação) ficam em config.local.json, fora do git; modelo em config.example.json.
"""
import sys, os, re, json, glob, shutil, zipfile, unicodedata
import xml.etree.ElementTree as ET


def carregar_config():
    arq = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.local.json")
    if not os.path.exists(arq):
        raise SystemExit(f"Falta {arq}: copie config.example.json para config.local.json e preencha seus dados")
    return json.load(open(arq, encoding="utf-8"))


CONFIG = carregar_config()
PASTA_PADRAO = CONFIG.get("pasta_dados", "")
LEGISLACAO = CONFIG.get("legislacao", "Portaria nº 359/GC4, de 6 de abril de 2016")
ANEXAR_BOLETIM = False
DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "FEP anexos")
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
T = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
X = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def norm(s):
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def ler_aba(ods, aba):
    root = ET.fromstring(zipfile.ZipFile(ods).read("content.xml"))
    for t in root.iter(T + "table"):
        if t.get(T + "name") != aba:
            continue
        rows = []
        for r in t.iter(T + "table-row"):
            row = []
            for c in r:
                if c.tag not in (T + "table-cell", T + "covered-table-cell"):
                    continue
                n = int(c.get(T + "number-columns-repeated", "1"))
                v = " ".join("".join(p.itertext()) for p in c.iter(X + "p")).strip()
                row += [v] * min(n, 60)
            rows.append(row)
        return rows
    raise SystemExit(f"Aba '{aba}' não encontrada no efetivo")


def efetivo(pasta):
    ods = sorted(glob.glob(os.path.join(pasta, "*.ods")))
    if not ods:
        raise SystemExit(f"Nenhuma planilha .ods em {pasta}")
    rows = ler_aba(ods[0], "EFETIVO")
    hi = next(i for i, r in enumerate(rows) if "SARAM" in [norm(c) for c in r])
    H = [norm(c) for c in rows[hi]]
    col = {k: H.index(k) for k in ["SARAM", "NOME COMPLETO", "NOME DE GUERRA", "GRAD", "TURMA", "CPF"] if k in H}
    out = []
    for r in rows[hi + 1:]:
        r = r + [""] * 40
        s = re.sub(r"\D", "", r[col["SARAM"]])
        if len(s) == 7:
            out.append({"saram": s, "nome": norm(r[col["NOME COMPLETO"]]), "guerra": norm(r[col["NOME DE GUERRA"]]),
                        "grad": r[col["GRAD"]].strip(), "turma": r[col["TURMA"]].strip(),
                        "tem_cpf": len(re.sub(r"\D", "", r[col["CPF"]])) == 11 if "CPF" in col else False})
    return out


def achar(pasta, chave):
    pdfs = glob.glob(os.path.join(pasta, "**", "*.pdf"), recursive=True)
    return [p for p in pdfs if chave(os.path.basename(p))]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    busca, pasta, mes_pedido, ano_pedido = norm(sys.argv[1]), PASTA_PADRAO, None, None
    for a in sys.argv[2:]:
        nm = [i for i, n in enumerate(MESES) if norm(n) in norm(a)]
        if nm and not os.path.isdir(a):
            mes_pedido = nm[0] + 1
            y = re.search(r"\b(20\d\d)\b", a)
            ano_pedido = int(y.group(1)) if y else None
        else:
            pasta = a
    ef = efetivo(pasta)
    cand = [m for m in ef if m["saram"] == re.sub(r"\D", "", busca)] if re.fullmatch(r"\d{7}", re.sub(r"\D", "", busca) or "x") else \
        [m for m in ef if m["guerra"] == busca] or [m for m in ef if busca in m["guerra"]]
    erros = []
    if len(cand) != 1:
        print(json.dumps({"ok": False, "erro": f"{len(cand)} militares encontrados para '{busca}'",
                          "candidatos": [{k: m[k] for k in ("saram", "guerra", "nome", "turma")} for m in cand]}, ensure_ascii=False, indent=1))
        return
    m = cand[0]
    s = m["saram"]
    import pymupdf

    def datas_pdf(p):
        txt = " ".join(pg.get_text() for pg in pymupdf.open(p))
        return sorted({(int(y), int(mo), int(d)) for d, mo, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", txt)})

    def mes_de(ds):
        c = {}
        for y, mo, _ in ds:
            c[(y, mo)] = c.get((y, mo), 0) + 1
        return max(c, key=c.get) if c else (0, 0)

    # one Parte de Etapa per month: pick the requested month, or the most recent one
    todas = [(mes_de(datas_pdf(p)), p) for p in achar(pasta, lambda f: f.upper().startswith("ETAPA EVENTUAL") and f.endswith(f"{s}.pdf"))]
    disponiveis = sorted({f"{MESES[mo - 1]} {y}" for (y, mo), _ in todas if mo}, key=lambda t: (int(t.split()[1]), [norm(n) for n in MESES].index(norm(t.split()[0]))))
    if mes_pedido:
        todas = [t for t in todas if t[0][1] == mes_pedido and (ano_pedido is None or t[0][0] == ano_pedido)]
    elif todas:
        ult = max(t[0] for t in todas)
        todas = [t for t in todas if t[0] == ult]
    etapas = [p for _, p in todas]
    fichas = [p for p in achar(pasta, lambda f: not f.upper().startswith(("ETAPA", "BOLETIM")) and f.endswith(f"{s}.pdf"))]
    if len(etapas) != 1:
        erros.append(f"{len(etapas)} Partes de Etapa encontradas para o SARAM {s}" + (f" em {MESES[mes_pedido - 1]}" if mes_pedido else "")
                     + (f" (meses disponíveis: {', '.join(disponiveis)})" if disponiveis else ""))
    if len(fichas) != 1: erros.append(f"{len(fichas)} Fichas Anuais encontradas para o SARAM {s}")
    if not m["tem_cpf"]: erros.append("militar sem CPF no efetivo")
    lac = {}
    if len(etapas) == 1:
        doc = pymupdf.open(etapas[0])
        ds = datas_pdf(etapas[0])
        meses = {(y, mo) for y, mo, _ in ds}
        if len(meses) != 1:
            erros.append(f"a Parte de Etapa tem datas de {len(meses)} meses")
        if ds:
            y, mo = ds[0][0], ds[0][1]
            lac = {"mes": MESES[mo - 1], "ano": str(y), "datas": ",".join(f"{d:02d}" for _, _, d in ds),
                   "legislacao": LEGISLACAO, "folhas_etapa": len(doc), "qtd_dias": len(ds)}
    # Cópia da escala: the per-militar boletim built by monta_boletins.py; a permuta goes without it.
    # Since 2026-11-03 the user sends the FEP with only ficha + etapa, so this stays off unless ANEXAR_BOLETIM is turned back on.
    boletim, bol_status = None, "não anexar: FEP vai só com ficha anual e etapa eventual"
    if lac and ANEXAR_BOLETIM:
        sit_arq = os.path.join(pasta, "BOLETIM", f"BOLETINS POR MILITAR - {lac['mes'].upper()} {lac['ano']}", "situacao.json")
        if not os.path.exists(sit_arq):
            bol_status = f"nao_montado: rode  python -I monta_boletins.py \"{lac['mes']} {lac['ano']}\"  e repita"
        else:
            st = json.load(open(sit_arq, encoding="utf-8")).get(s)
            if not st:
                bol_status = "militar fora da montagem dos boletins: rode monta_boletins.py de novo"
            elif st["situacao"] == "permuta":
                bol_status = "permuta: NÃO anexar boletim (FEP só com etapa e ficha)"
            elif st["situacao"].startswith("ok") and st.get("arquivo") and os.path.exists(st["arquivo"]):
                boletim = st["arquivo"]
                bol_status = "anexar" + (f" (nome ausente no boletim em {st['sem_nome']})" if st.get("sem_nome") else "")
            else:
                erros.append(f"boletim: {st['situacao']}" + (f" {st.get('faltam')}" if st.get("faltam") else ""))
                bol_status = st["situacao"]
    anexos = {}
    if not erros:
        dest = os.path.abspath(os.path.join(DESTINO, f"{lac['mes']} {lac['ano']}"))
        os.makedirs(dest, exist_ok=True)
        for k, src in (("ficha_anual", fichas[0]), ("parte_etapa", etapas[0])) + ((("escala", boletim),) if boletim else ()):
            shutil.copy2(src, dest)
            anexos[k] = os.path.join(dest, os.path.basename(src))
    print(json.dumps({"ok": not erros, "erros": erros, "militar": {k: m[k] for k in ("saram", "guerra", "nome", "grad", "turma")},
                      "lacunas": lac, "chefe_imediato": CONFIG.get("chefe_imediato", {}), "anexos": anexos, "meses_com_etapa": disponiveis, "boletim": bol_status},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
