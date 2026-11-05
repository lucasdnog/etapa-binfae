---
name: realizar-fep
description: Preenche no Portal do Militar (FEP) o requerimento de Etapa Eventual 5x de um ou vários militares (fila), com lacunas, chefe imediato e anexos. Espera o usuário fazer o login de cada militar, retoma sozinho quando o portal carrega e só envia com "sim" explícito. Use quando o usuário digitar /realizar-fep ou disser "realizar FEP".
---

# Realizar FEP (Etapa Eventual 5x)

Quem faz o login é **sempre o usuário**, no navegador dele (Claude in Chrome). **Nunca** digite senha, CPF ou faça login, nunca faça logout e nunca troque de conta: quando precisar de outra conta, peça ao usuário e espere (seção 0).

Argumentos opcionais, em qualquer ordem:
- **militares** da fila: nomes de guerra ou SARAM separados por vírgula (ex.: `/realizar-fep FULANO, SILVA, 1234567 novembro`). Sem nomes, a fila é só o militar que estiver logado (comportamento antigo).
- o **mês** da etapa (ex.: `novembro`).
- a **pasta** dos dados (padrão: `pasta_dados` em `config.local.json`).

**Dados pessoais** (pasta dos dados, chefe imediato, legislação) ficam em `config.local.json`, nesta pasta da skill. Ele não vai para o GitHub; o modelo é `config.example.json`. Se faltar, os scripts avisam: copie o modelo e preencha.
- `teste`: **modo teste**, um militar só. Faz tudo (login, seções 1 a 5, conferência dos anexos) e para na tabela de conferência **sem enviar, mesmo que o usuário diga "sim"**: para enviar, ele precisa rodar de novo sem `teste`. No fim, deixe o formulário preenchido na tela (não clique em Enviar nem em Limpar) e diga que nada foi gravado no sistema. Com `teste`, ignore nomes extras (sem fila) e não grave `fila FEP.md`.

O site grava cada mês numa pasta `ETAPAS EVENTUAIS - MÊS`; sem mês, o script usa a etapa mais recente do militar, e você deve dizer ao usuário qual mês foi usado (campo `meses_com_etapa` lista os outros). Ela tem o efetivo `.ods` (aba EFETIVO), a pasta das Partes de Etapa (`Etapa Eventual - ... - SARAM.pdf`), a pasta `FICHAS ESI` (`NOME - SARAM.pdf`) e, quando houver, uma pasta com `BOLETIM` ou `ESCALA` no nome com **um** PDF (cópia da escala, igual para todos).

## 0. Sessão e login (antes de tudo, e sempre que a página mudar de conta)

### 0.1 Verificar o estado da aba

Carregue as ferramentas do Chrome numa chamada só (tabs_context_mcp, navigate, computer, find, read_page, form_input, javascript_tool, file_upload, get_page_text) e ache a aba `apl1.sti.fab.mil.br` (FEP ou Portal). Se não houver, abra `https://apl1.sti.fab.mil.br/fep/` numa aba do grupo. Rode:

```js
(()=>{const vis=e=>!!(e&&e.offsetParent!==null);
const txt=(document.body?.innerText||'').replace(/\s+/g,' ');
const pw=[...document.querySelectorAll('input[type=password]')].some(vis);
const botoes=[...document.querySelectorAll('a,button,input[type=submit]')].filter(vis).map(b=>(b.innerText||b.value||'').trim());
const escolha=botoes.some(b=>/Entrar com Gov\.?Br/i.test(b))||botoes.some(b=>/Entrar com Login [ÚU]nico/i.test(b));
const sso=/(^|\.)login\.sti\.fab\.mil\.br$|(^|\.)acesso\.gov\.br$/.test(location.host);
const manut=/manuten[çc][ãa]o/i.test(document.title)||/SSL handshake failed|Error code 5\d\d|Error reference number: 5\d\d/i.test(txt);
const expir=/sess[ãa]o (expirad|encerrad|inv[áa]lid)|ViewExpired/i.test(txt);
const hdr=[...document.querySelectorAll('header, .topbar, .layout-topbar, nav')].map(e=>e.innerText).join(' ').replace(/\s+/g,' ').trim();
const m=hdr.match(/\b(S2|S1|CB|3S|2S|1S|SO|AS|2T|1T|CP|MJ|TC|CL)\s+([A-ZÀ-Ú][A-ZÀ-Ú\- ]*?)\s+GSD-AF/);
const logado=!!m&&!pw&&!manut;
const estado=manut?'manutencao':logado?'logado':sso||pw?'login_credenciais':escolha?'login_escolha':expir?'sessao_expirada':'indefinido';
return {estado, url:location.origin+location.pathname, titulo:document.title, posto:m?.[1], guerra:m?.[2], cabecalho:hdr.slice(0,120)};})()
```

Decida pelo campo `estado`:

| `estado` | O que é | O que fazer |
|---|---|---|
| `logado` | Portal ou FEP com cabeçalho `POSTO GUERRA GSD-AF` | Leia `posto`/`guerra` e siga |
| `login_escolha` | `apl1.sti.fab.mil.br/portal/` com os botões **"Entrar com Gov.Br"** e **"Entrar com Login Único"** (sem campo de senha) | 0.2 — peça o login |
| `login_credenciais` | Tela de CPF/senha: `login.sti.fab.mil.br/authenticationendpoint/login.do` (Login Único) ou `*.acesso.gov.br` (Gov.br) | 0.2 — o usuário já está entrando; só espere |
| `sessao_expirada` | Aviso de sessão expirada/encerrada | 0.3 |
| `manutencao` | Título "Sistema em manutenção" / "SSL handshake failed" / erro 5xx (ex.: 525 do Cloudflare) | **Pare** e avise que o sistema está fora do ar; não peça login. Pode tentar de novo 1 vez após ~30 s (só navegar para a mesma URL) |
| `indefinido` | Página em carregamento ou desconhecida. Inclui a verificação do Cloudflare (título "Um momento…", "Executando verificação de segurança"), que em 05/11/2026 passou sozinha em ~10 s | Espere 5–10 s e rode de novo, **sem clicar** na verificação; persistindo (ou se pedir para marcar uma caixa), peça ao usuário para resolver e espere como em 0.2 |

Fluxo real do login (validado em 05/11/2026): `portal/` (`login_escolha`) → usuário clica Login Único → `login.sti.fab.mil.br/...login.do` (`login_credenciais`) → usuário entra → `apl1.sti.fab.mil.br/portal/faces/index.xhtml` com `S2 BELTRANO GSD-AF` (`logado`). A detecção acontece até 10 s depois do redirecionamento. Logo após uma navegação o título/cabeçalho podem vir vazios por 1–2 s: isso é `indefinido`, não falta de login.

Atenção: a página do FEP tem um campo de senha **escondido** (diálogo "Assinatura Eletrônica"); por isso o script só conta campos de senha visíveis. **Nunca** preencha esse diálogo: se ele aparecer visível, pare e avise o usuário.

### 0.2 Pedir o login e esperar sozinho

1. Diga ao usuário, numa linha, de quem é o login: *"Faça o login do **S2 FULANO** no Chrome; eu continuo sozinho assim que o portal carregar."* Na fila, diga também quantos faltam.
2. **Não termine o turno.** Monitore a mesma aba com `browser_batch`: 3 pares de `computer wait 10` + o script de 0.1 por chamada, repetindo até `estado: "logado"`. Limite: **10 minutos**. Não clique, não digite e não navegue enquanto espera (o usuário está usando a aba).
   - Ao ver `login_credenciais`, avise numa linha "tela de CPF/senha aberta, aguardando" (uma vez só).
   - Se ficar ~3 min em `login_escolha` sem a URL mudar, lembre numa linha que o login deve ser feito **nesta aba** (a do grupo do Claude, título ".::: CCA-RJ :::."); login feito em outra aba não aparece aqui.
   - `manutencao` durante a espera → pare e avise (0.1).
3. Quando `estado: "logado"`:
   - se o usuário caiu no Portal e não no FEP, navegue para `https://apl1.sti.fab.mil.br/fep/`;
   - confira se `guerra` é o militar esperado (o item atual da fila). Se for **outro**, não preencha nada: avise ("está logado o S2 X, eu esperava o S2 Y") e volte a esperar.
   - Avise numa linha "Login do S2 Y detectado, continuando" e siga.
4. Passou dos 10 minutos sem login → pare, diga que a fila está pausada no militar Y e que basta responder "pronto" (ou rodar a skill de novo) para continuar.

### 0.3 Sessão expirada no meio do trabalho

Rode o script de 0.1 ao começar cada militar, depois dos anexos e **imediatamente antes** de enviar. Se vier `manutencao` (ex.: erro 525), pause do mesmo jeito, mas avise que é o sistema fora do ar e **não** peça login; o usuário diz quando tentar de novo. Se a sessão caiu (`login_escolha`, `login_credenciais`, `sessao_expirada`, ou o cabeçalho sumiu):
1. Pause: não tente reenviar nem recarregar. Anote em que passo parou.
2. Peça novo login do **mesmo** militar e espere como em 0.2.
3. Depois do login, **refaça o formulário desse militar do início** (seções 2 a 5), porque o portal perde o que não foi enviado. Os dados do script continuam valendo, não precisa rodar de novo.

### 0.4 Sessão entre militares

- Ao terminar um militar, **não faça logout**. Deixe a sessão como está.
- Se o próximo da fila for o mesmo militar que já está logado, siga direto, sem pedir login.
- Se for outro, peça ao usuário para **sair da conta atual e entrar com o próximo** (você não clica em Sair) e espere como em 0.2. O portal só aceita um militar por vez na mesma aba, então a troca de conta é sempre do usuário.

## F. Fila de militares (só quando o usuário passar nomes)

1. **Preparar tudo antes de abrir o portal:** para cada nome/SARAM da fila, rode `fep_dados.py` (seção 1, passo 3) com o mesmo mês e pasta.
2. Mostre uma tabela da fila: posição, militar (posto, guerra, SARAM), mês, quantidade de dias, anexos ok, e erros. Quem voltar `ok: false` fica marcado **"não processado"** com o motivo (nome repetido, sem etapa, sem ficha, sem CPF no efetivo) e sai da fila; peça o SARAM quando o problema for nome repetido.
3. Grave o andamento em `ClaudeCode\FEP anexos\<Mês Ano>\fila FEP.md` (tabela com status: pendente, aguardando login, preenchido, enviado, erro, não processado + a mensagem do sistema). Atualize a cada mudança de status. Ao começar, se o arquivo já existir com pendentes da mesma fila, ofereça retomar de onde parou.
4. Processe um militar por vez: seção 0 (login do militar) → seções 1 a 5 → aguarde o "sim/enviar" **deste** militar → envie → registre o resultado → próximo (0.4).
5. No fim, mostre o resumo da fila: enviados, com erro, não processados.

## 1. Identificar o militar

1. (Ferramentas e aba: já feito em 0.1.)
2. Leia o nome de guerra no canto superior direito (ex.: `S2 FULANO GSD-AF` → `FULANO`). Na fila, ele tem de ser o militar da vez (0.2, passo 3).
3. Rode o script, a partir desta pasta da skill (na fila, já foi rodado em F.1; reuse o resultado):
   `python -I fep_dados.py "NOME DE GUERRA" [MÊS] ["PASTA"]` (ex.: `python -I fep_dados.py "FULANO" novembro`)
   - `ok: false` → **pare** e mostre ao usuário o erro e os candidatos (ex.: dois militares com o mesmo nome de guerra; ele pode responder com o SARAM, e você roda o script com o SARAM).
   - (só se `ANEXAR_BOLETIM` estiver ligado) campo `boletim` começando com `nao_montado` → rode o comando que ele indica (`python -I monta_boletins.py "Outubro 2026"`), mostre ao usuário o resumo que ele imprime (permutas, dias sem nome, boletins faltando) e rode `fep_dados.py` de novo.
   - `ok: true` → use `militar`, `lacunas` e `anexos` (caminhos já copiados para `ClaudeCode\FEP anexos\<Mês Ano>`, a única pasta de onde o navegador consegue anexar).

## 2. Cadastrar FEP

1. Menu ☰ (topo) › **Cadastrar FEP** (ou navegue para `https://apl1.sti.fab.mil.br/fep/cadastrarFormularioEletronicoPessoal.xhtml`).
2. **Solicitação**: no `<select>` nativo `frmSolicitacao:...:grupoSolicitacaoCombo_input`, `form_input` com o valor `16` (Etapa Eventual). Espere ~2 s.
3. **Tipo de Solicitação**: é um dropdown PrimeFaces. Clique nele e clique em **Concessão 5(Cinco) Vezes A Etapa Comum**. Espere aparecer o "Formulário Pessoal".
4. **Lacunas** (inputs com id `1`, `2`, `3`, `4`; ache pelos placeholders com `find`). Clique e digite em cada um:
   - MÊS → `lacunas.mes` (por extenso, ex.: Outubro)
   - ANO → `lacunas.ano`
   - DATA(S) DE CONCESSÃO → `lacunas.datas` (vírgulas **sem espaço**, como o próprio campo exige: `03,06,09`)
   - LEGISLAÇÃO → `lacunas.legislacao`
   Depois pressione Tab.

Dica (05/11/2026): se o `form_input` não mudar os selects de Solicitação/Tipo, funciona por JavaScript: `s.value='16'` (depois `'52'` no `tipoSolicitacaoCombo_input`) + `s.dispatchEvent(new Event('change',{bubbles:true}))`, esperando ~3 s entre os dois.

## 3. Anexos

Tabela "Lista de Formulários Eletrônicos de Pessoal" (file inputs `frmSolicitacao:tabViewFormPessoal:tbl:N:fileUpload_input`):
- linha 0 **CÓPIA DA ESCALA DE SERVIÇO** → **deixe em branco**. Decisão do usuário em 03/11/2026: o FEP vai só com Ficha Anual e Parte de Etapa (o script já não devolve `anexos.escala`). Histórico, caso ele volte a pedir (`ANEXAR_BOLETIM = True` em `fep_dados.py`): `anexos.escala` era o PDF com os boletins diários dos dias de serviço do militar, montado por `monta_boletins.py` (boletins diários em `<pasta>\BOLETIM\<MÊS AAAA>\DD.MM.pdf`, boletim do próprio dia; saída em `BOLETIM\BOLETINS POR MILITAR - <MÊS AAAA>`). Se `boletim` disser **permuta** (militar com 1–2 dias cujo nome não está no boletim), deixe essa linha em branco: o FEP vai só com etapa e ficha — regra do usuário. Se disser "nome ausente em …", anexe e avise o usuário desses dias.
- linha 1 **FICHA ANUAL DE CADASTRO DA ETAPA EVENTUAL** → `anexos.ficha_anual`
- linha 2 **PARTE DE ETAPA EVENTUAL CINCO VEZES** → `anexos.parte_etapa` (PDF inteiro, mesmo com 2 folhas)

Use `find` para pegar o ref de cada file input **depois** de cada upload (a página re-renderiza) e `file_upload` com o caminho. Não clique no botão "Choose".

## 4. Chefe imediato — o de `chefe_imediato` na saída do script

Os dados do chefe vêm de `config.local.json` (campo `chefe_imediato`: `posto`, `om`, `nome_guerra`, `nome_completo`). Se o campo vier vazio, pare e peça ao usuário para preencher o `config.local.json`.

1. No bloco "Dados do Chefe Imediato", clique na lupa 🔍 ao lado de **Seção** → abre "Cadastrar Chefe Esporádico".
2. Posto: `chefe_imediato.posto`; OM: `chefe_imediato.om` (dropdowns PrimeFaces: clique e escolha).
3. Nome de Guerra: `chefe_imediato.nome_guerra` → **Pesquisar**.
4. Marque a linha com o `nome_completo` e a OM do chefe e clique **Confirmar**.
5. O campo Chefe Imediato deve mostrar o posto abreviado + `nome_completo` (ex.: `1T NOME COMPLETO`). Se não achar, pare e avise.

Dica (05/11/2026): esse diálogo só abre com a janela do Chrome **visível** na tela. Se o screenshot der timeout ou o diálogo continuar com `display: none` depois do clique, peça ao usuário para trazer o Chrome para a frente. Não force os dropdowns por JavaScript: a pesquisa volta "Não há registro" e o nome se apaga.

## 5. Conferir e parar

Confirme por JavaScript que nada se perdeu:

```js
const tbl=document.getElementById("frmSolicitacao:tabViewFormPessoal:tbl");
({vals:["1","2","3","4"].map(i=>document.getElementById(i)?.value),
  docs:[...tbl.querySelectorAll("tbody tr")].map(tr=>tr.innerText.replace(/\s+/g," ").trim()),
  chefe:[...document.querySelectorAll('[id^="frmSolicitacao:tabChefeImediato:"]')].filter(i=>i.tagName==="INPUT").map(i=>i.value)})
```

Mostre ao usuário uma tabela: militar (posto, guerra, nome, SARAM), mês, ano, datas (e quantidade), legislação, os 3 anexos (escala em branco quando for o caso), chefe imediato. Na conferência dos anexos, compare o nome de cada arquivo na tabela do portal com `anexos.ficha_anual` e `anexos.parte_etapa` (mesmo SARAM do militar logado) e a linha da escala vazia. Em **modo teste**, pare aqui. **Não clique em "Enviar Formulário"** sem um "sim/enviar" explícito do usuário para **este** militar (na fila, um "sim" vale só para o militar mostrado, nunca para os próximos). Depois de enviar, leia a mensagem do sistema (growl/mensagem na página) e relate o resultado exato, inclusive erro por falta da cópia da escala.

Ao enviar: o portal abre "Confirma chefia selecionada?" mostrando o chefe. Se for o chefe de `chefe_imediato` (nome e OM), clique **Confirmar** (faz parte do envio já autorizado); se for outro, clique **Negar** e avise. Sucesso = aviso "Formulário Eletrônico de Pessoal enviado com Sucesso!". Se aparecer o diálogo **Assinatura Eletrônica** (CPF e senha) visível, pare: quem assina é o usuário.

Depois do envio, na fila: registre o resultado em `fila FEP.md` e siga para o próximo (0.4), **sem logout**.

## Regras

- Nunca digitar senha ou CPF, nunca fazer login, nunca fazer logout, nunca trocar de conta: login, saída e troca de conta são sempre do usuário.
- Enquanto espera o login, não mexa na aba (só leia o estado).
- Se o militar logado não tiver etapa no mês, ficha, ou CPF no efetivo, pare e avise sem preencher.
- Um "sim/enviar" vale para um militar só.
- Os ids `j_idt..` do PrimeFaces podem mudar entre versões: prefira `find` pelos rótulos.
