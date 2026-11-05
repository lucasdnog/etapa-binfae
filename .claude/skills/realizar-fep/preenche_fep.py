import subprocess
import json
import os
from playwright.sync_api import sync_playwright

def executar_fep_dados(militar_busca):
    """Chama o seu script atual para extrair os dados e gerar o JSON."""
    cmd = ["python", "-I", "fep_dados.py", militar_busca]
    print(f"Executando extração para: {militar_busca}...")
    
    resultado = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    if resultado.returncode != 0:
        print(f"Erro ao executar fep_dados.py:\n{resultado.stderr}")
        return None

    try:
        return json.loads(resultado.stdout)
    except json.JSONDecodeError:
        print("Erro: A saída do fep_dados.py não gerou um JSON válido:", resultado.stdout)
        return None

def main():
    # 1. Pergunta qual militar você quer processar
    militar_busca = input("Digite o Nome de Guerra ou SARAM do militar: ")
    dados = executar_fep_dados(militar_busca)
    
    if not dados or not dados.get("ok"):
        print("❌ Erro nos dados extraídos:", dados.get("erros", "Desconhecido"))
        return

    # Exibe resumo do que foi encontrado pelo seu script
    m = dados["militar"]
    l = dados["lacunas"]
    print(f"\n[SUCESSO] Militar: {m['grad']} {m['guerra']} (SARAM: {m['saram']})")
    print(f"Período: {l['mes']}/{l['ano']} - Dias: {l['datas']}")
    print(f"Anexos prontos em: {list(dados['anexos'].values())}\n")

    # 2. Abre o navegador automatizado com Playwright
    with sync_playwright() as p:
        # Cria uma pasta local para salvar a sessão/cookies e evitar login repetido
        user_data_dir = os.path.join(os.path.dirname(__file__), "perfil_browser_militar")
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False # Deixa o navegador visível para você acompanhar
        )
        
        page = browser.new_page()
        
        # Substitua pela URL exata da página de preenchimento do FEP no Portal do Militar
        url_portal = "https://sua-url-do-portal-do-militar-aqui.com.br"
        page.goto(url_portal)

        print("==================================================")
        print("🔐 AVISO DE LOGIN:")
        print("Se esta for a primeira execução, uma janela do navegador vai abrir.")
        print("Faça o seu login normal com CPF e senha (ou gov.br) manualmente lá.")
        print("Assim que estiver logado na tela de preenchimento, volte aqui e aperte ENTER.")
        print("==================================================")
        input("Pressione ENTER após estar logado para o script continuar...")

        print("🤖 Preenchendo os campos automaticamente...")
        
        # EXEMPLOS DE AÇÕES DE PREENCHIMENTO (Você ajustará com os seletores reais da página):
        # page.fill("#campo_saram", m["saram"])
        # page.fill("#campo_dias", l["datas"])
        
        # Exemplo anexando os arquivos PDF gerados pelo fep_dados.py:
        # arquivos = list(dados["anexos"].values())
        # page.set_input_files("input[type='file']", arquivos)

        print("✨ Preenchimento concluído! Revise na tela do navegador e clique em enviar.")
        
        input("Pressione ENTER aqui no terminal para fechar o navegador...")
        browser.close()

if __name__ == "__main__":
    main()