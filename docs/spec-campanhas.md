# Campanhas (pedido de 15/09/2026)

Aba nova tipo painel. A conta master publica campanhas (excursões que o resort quer vender);
vendedores pegam a campanha, fazem a arte com o próprio telefone e informam as vendas.
Base: pesquisa em CRMs (HubSpot/Salesforce campaigns), portais de parceiros (Allbound, Impartner),
Rezdy e sistemas de excursão brasileiros (Viagilize, Excapy).

## Papéis
| | master | vendedor |
|---|---|---|
| Criar/editar/pausar/encerrar campanha, montar a arte | sim | não |
| Ver campanhas | todas | ativas, pausadas e encerradas (não vê rascunho) |
| Pegar campanha, fazer arte, informar venda | sim | sim |
| Ver vendas | de todos, confirma/cancela | só as dele |
| Ranking de vendedores | sim | não |

(O papel adsign existiu de 15 a 17/09/2026 e foi removido.)

## Campanha
- **Básico:** nome, resumo, status (rascunho / ativa / pausada / encerrada; "esgotada" é calculado), data limite de venda.
- **Viagem:** ida, volta, pontos de embarque (um por linha: local e horário), horário de retorno.
- **Valores:** valor por pessoa, parcelas, sinal/entrada, quitar até, formas de pagamento, regra de crianças, comissão.
- **Vagas:** total. Vendidas = soma das pessoas das vendas não canceladas de todos os vendedores; restantes = total − vendidas.
- **Informações:** roteiro, o que inclui, o que não inclui, documentos exigidos, política de cancelamento, regras, contato do guia.
- **Materiais:** textos prontos pro WhatsApp (botão copiar) e links (Drive, PDF, vídeo).
- **Arte:** montada no mesmo editor passo a passo. O vendedor que pega a campanha só troca o telefone
  (datas, valor, título e foto travados — decisão do usuário).

## Venda
cliente, telefone, pessoas, ponto de embarque, forma de pagamento, sinal pago (sim/não), observação,
status (pendente → confirmada / cancelada pela master). Não aceita se passar das vagas restantes, se a
campanha não está ativa ou se passou a data limite.

## Telas
- `#/campanhas` — vitrine. Master: "Nova campanha" + abas Ativas / Rascunhos / Pausadas / Encerradas.
  Vendedor: abas Disponíveis / Minhas / Encerradas. Card: miniatura, datas, valor, barra de vagas, prazo.
- `#/campanha/<id>` — ficha completa + materiais + ações (Fazer minha arte, Informar venda, Minhas vendas;
  master: vendas de todos com confirmar/cancelar e ranking; editar, mudar status).
- `#/campanha-editar/<id|nova>` — formulário em seções.

## Servidor (ações)
`campanhas`, `salvarCampanha`, `excluirCampanha` (só sem vendas), `pegarCampanha`, `vendas`, `salvarVenda`.
Planilha: abas **Campanhas**, **Vendas** e **Participantes**. Implementado no `Codigo.gs` (17/09/2026), no servidor falso e no `demoApi()`; contrato em `docs/api.md`.

## Fora desta fase
Lista de passageiros com documento, lista de espera, mapa de poltronas/rooming list, reserva que expira sem sinal,
avisos para todos, link rastreável, relatório de comissão, histórico de alterações, envio de arquivo (usar link).
