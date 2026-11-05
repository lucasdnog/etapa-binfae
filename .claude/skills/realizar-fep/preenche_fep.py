import subprocess
import json
import sys
import time
from playwright.sync_api import sync_playwright


def calcular_senha_turma(turma):
    """Gera a senha padrão com base na turma do militar (ex: '1/24' -> 'Recruta124@')."""
    if not turma or "/" not in turma:
        return ""
    partes = turma.split("/")
    num = ''.join(filter(str.isdigit, partes[0]))
    ano = ''.join(filter(str.isdigit, partes[1]))
    return f"Recruta{num}{ano}@"


def executar_fep_dados(militar_busca):
    cmd = ["python", "-I", "fep_dados.py", militar_busca]
    resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if resultado.returncode != 0:
        print(f"Erro ao extrair dados: {resultado.stderr}")
        return None

    try:
        return json.loads(resultado.stdout)
    except json.JSONDecodeError:
        print("Erro ao ler JSON gerado:", resultado.stdout)
        return None


def main():
    if len(sys.argv) > 1:
        busca = sys.argv[1]
    else:
        busca = input("Digite o Nome de Guerra ou SARAM do militar: ")

    dados = executar_fep_dados(busca)

    if not dados or not dados.get("ok"):
        print("❌ Erro nos dados:", dados.get("erros", "Militar não encontrado."))
        return

    m = dados["militar"]
    l = dados["lacunas"]
    anexos = list(dados["anexos"].values())

    # Descobre a senha automaticamente com base na turma do militar
    senha_militar = calcular_senha_turma(m.get("turma", ""))

    if not m.get("cpf") or len(m["cpf"]) != 11:
        print(f"❌ Erro: O militar {m['guerra']} não possui um CPF válido cadastrado na planilha.")
        return

    if not senha_militar:
        print(f"❌ Erro: Não foi possível calcular a senha para a turma '{m.get('turma')}' do militar {m['guerra']}.")
        return

    print(f"\n🚀 Militar: {m['grad']} {m['guerra']} | Turma: {m['turma']} | Senha gerada: {senha_militar}")
    print(f"📅 Período: {l['mes']}/{l['ano']} ({l['qtd_dias']} dias)")

    # Abre o navegador para realizar o login individual com o CPF e a senha da turma dele
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Substitua pela URL real de login do Portal do Militar
        page.goto("URL_DO_PORTAL_DO_MILITAR_LOGIN")

        print("🔑 Realizando login automático...")

        # Ajuste os seletores CSS se os nomes dos campos no portal forem diferentes
        page.fill("input[name*='cpf']", m["cpf"])
        page.fill("input[name*='senha']", senha_militar)
        page.click("button[type='submit']")

        page.wait_for_load_state("networkidle")
        time.sleep(2)

        print("🤖 Navegando para o FEP e preenchendo...")

        # Exemplo de preenchimento dos campos e anexos:
        # page.fill("#campo_dias_etapa", l["datas"])
        # page.set_input_files("input[type='file']", anexos)

        print(f"✨ FEP de {m['guerra']} logado e pronto! Revise na tela e envie.")

        input("Pressione ENTER aqui no terminal para fechar o navegador deste militar...")
        browser.close()


if __name__ == "__main__":
    main()