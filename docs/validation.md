# Validação local

Em 26/09/2026, Omarchy 4.0.4-1, Qt Multimedia 6.11.2, StreamCam conectada por USB High-Speed.

| Verificação | Resultado |
| --- | --- |
| `omarchy plugin validate .` | Passou |
| `qmllint` nos três componentes QML, usando os imports do shell instalado | Passou |
| `shellcheck install-local.sh` | Passou |
| `python3 -m unittest discover -s tests -v` | 15 testes passaram |
| Leitura real de controles pelo helper | 17 controles, nó de metadados ignorado |
| Escrita real do brilho | 128 → 129 → 128, restauração verificada |
| Abertura em Quickshell isolado | Carregou, apresentou controles e tema nativo |
| Prévia real Qt Multimedia | Recebeu frames |
| Fechar e reabrir | Captura liberada; prévia permanece desligada ao reabrir |
| Outra captura mantendo a câmera ocupada | Erro “Camera is in use” apresentado; 17 controles continuam disponíveis |
| Import multimídia ausente, simulado no componente temporário | Erro orientando instalação; painel e 17 controles continuam disponíveis |

Os testes Python cobrem faixas e passos, menus com lacunas, controles inativos, somente leitura e bloqueados, nomes desconhecidos, rejeição de injeção, releitura após escrita, dispositivo selecionado ausente, timeout, dependência ausente, permissão negada e execução sem shell.

A inspeção visual do painel foi feita na sessão Wayland. O teste da prévia verificou a chegada dos frames; não grava imagens nem áudio. Os valores automáticos de foco, exposição e balanço de branco podem mudar naturalmente enquanto a câmera captura.

A validação não mediu o efeito visual de todos os controles, nem testou uma conexão USB SuperSpeed/60 fps. A instalação persistente e publicação não fazem parte destes testes; os comandos para instalação estão no README.

## Internacionalização

O README passou a ser mantido em inglês. Interface, helper e instalador usam o catálogo compartilhado `translations.json`, com inglês e português. Testes adicionais verificam `pt_BR`, `pt_PT`, variantes de locale, prioridade `LC_ALL` → `LC_MESSAGES` → `LANG`, locale ausente/C/POSIX, idioma não suportado, tradução individual ausente e parâmetros interpolados. A seleção foi conferida tanto no Python quanto no componente QML em execução.

O smoke test completo passou com `LC_ALL=pt_BR.UTF-8`, incluindo frames da prévia, controles visíveis e fechamento/reabertura. Também passou com `LC_ALL=fr_FR.UTF-8`, usando o fallback em inglês e sem ativar a câmera. Esses testes usam a variável de ambiente diretamente; não exigem a instalação dos locales de teste no sistema.
