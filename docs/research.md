# Pesquisa: Omarchy e Logitech StreamCam

Consulta em 26/09/2026. Fontes: documentação e código oficiais, complementados por enumeração somente de leitura da webcam conectada. Os valores abaixo são uma observação deste equipamento; a interface deve descobrir novamente controles, faixas e formatos em cada dispositivo.

## Contrato do plugin Omarchy

O plugin vive em `~/.config/omarchy/plugins/<id>/`, com `manifest.json` na raiz e entradas QML. O manifesto exige `schemaVersion: 1`, `id`, `name`, `version`, `kinds` e `entryPoints`. O namespace `omarchy.*` é reservado. Este projeto usa um único `bar-widget` com painel interno, acessível pela barra e por IPC; não precisa declarar um segundo tipo `panel`. Fontes: [manual oficial de plugins](https://github.com/omacom/omarchy/blob/quattro/manual/32-shell-plugins.md), [guia de desenvolvimento](https://plugins.omarchy.org/develop.html).

O shell injeta propriedades declaradas pelo componente, como `shell`, `manifest` e `omarchyPath`. Plugins externos recebem interfaces limitadas ao próprio serviço/ciclo de vida; não se deve depender de propriedades privadas como `manifest.__sourceDir`. Um painel oferece `open(payloadJson)` e `close()`. Usar caminhos relativos ao próprio QML para localizar o backend. Fonte: [referência oficial do shell](https://github.com/omacom/omarchy/blob/quattro/docs/omarchy-shell.md), conferida também em `/usr/share/omarchy/shell/README.md` do Omarchy instalado, versão 4.0.4-1.

Instalação local: colocar os arquivos no diretório de plugins, executar `omarchy-shell shell rescanPlugins` e `omarchy plugin enable <id>`. Para distribuição, `omarchy plugin add <git-url> --enable` clona um repositório cujo manifesto está na raiz. Alterações locais recarregam o plugin. Fonte: [README oficial do shell](https://github.com/omacom/omarchy/blob/quattro/shell/README.md).

## Recursos documentados da StreamCam

A Logitech identifica a StreamCam como UVC, USB `046d:0893`, modelo V-U0054, com autofocus e microfones duplos. O suporte de software anunciado no lançamento é Logitech Capture para Windows/macOS. Fonte: [especificações técnicas da Logitech](https://support.logi.com/hc/en-gb/articles/360042528854-StreamCam-Technical-Specifications).

O produto anuncia até 1080p60. A Logitech recomenda conexão direta USB 3.1 Gen 1 Type-C para esse modo. Isso não garante que todos os formatos estejam disponíveis em qualquer porta, adaptador ou hub. Fontes: [página do produto](https://www.logitech.com/en-us/shop/p/streamcam), [requisitos para 1080p60](https://support.logi.com/hc/en-us/articles/360042073534-What-are-the-system-requirements-for-Logitech-StreamCam-when-used-with-Logitech-Capture).

## Controles confirmados no equipamento conectado

Fonte primária desta tabela: `v4l2-ctl -d /dev/video0 --list-ctrls-menus`, executado nesta máquina em 26/09/2026. A enumeração confirmou **17 controles**. Nenhum valor foi alterado nesta pesquisa.

| Ajuste | Nome V4L2 | Faixa ou opções | Padrão reportado |
| --- | --- | --- | --- |
| Brilho | `brightness` | 0–255, passo 1 | 128 |
| Contraste | `contrast` | 0–255, passo 1 | 128 |
| Saturação | `saturation` | 0–255, passo 1 | 128 |
| Balanço de branco automático | `white_balance_automatic` | 0 / 1 | 1 |
| Ganho | `gain` | 0–255, passo 1 | 0 |
| Anticintilação | `power_line_frequency` | 0: desligado; 1: 50 Hz; 2: 60 Hz | 2 |
| Temperatura do branco | `white_balance_temperature` | 2000–7500, passo 1 | 4000 |
| Nitidez | `sharpness` | 0–255, passo 1 | 128 |
| Compensação de contraluz | `backlight_compensation` | 0 / 1 | 0 |
| Modo de exposição | `auto_exposure` | 1: manual; 3: prioridade de abertura | 3 |
| Tempo de exposição | `exposure_time_absolute` | 3–2047, passo 1 | 250 |
| FPS variável com exposição automática | `exposure_dynamic_framerate` | 0 / 1 | 0 |
| Pan horizontal | `pan_absolute` | −36000–36000, passo 3600 | 0 |
| Tilt vertical | `tilt_absolute` | −36000–36000, passo 3600 | 0 |
| Foco manual | `focus_absolute` | 0–255, passo 1 | 0 |
| Autofoco contínuo | `focus_automatic_continuous` | 0 / 1 | 1 |
| Zoom | `zoom_absolute` | 100–400, passo 1 | 100 |

Os menus podem conter lacunas: a exposição informa limites 0–3, mas somente as entradas 1 e 3 existem. O plugin deve usar as entradas enumeradas, não gerar todos os inteiros entre os limites. Controles marcados `inactive`, `read-only`, `disabled` ou `grabbed` precisam ser refletidos na interface; uma alteração pode mudar o estado dos demais. Fonte: [V4L2 QUERYCTRL/QUERYMENU](https://docs.kernel.org/userspace-api/media/v4l/vidioc-queryctrl.html).

Na leitura inicial, temperatura do branco, tempo de exposição e foco manual estavam inativos porque seus automatismos estavam ligados. Para ajustá-los, desligar o automatismo correspondente e consultar novamente. A exposição absoluta usa unidades de 100 microssegundos: 250 equivale a 25 ms. O FPS dinâmico permite ao dispositivo variar a taxa de quadros durante exposição automática. Fonte: [referência de controles de câmera do kernel](https://docs.kernel.org/userspace-api/media/v4l/ext-ctrls-camera.html).

Pan/tilt e zoom foram enumerados; a pesquisa não realizou captura visual para medir seu efeito. A presença desses nomes V4L2 não comprova movimento mecânico da câmera. O plugin deve apresentá-los como enquadramento e evitar alegar PTZ motorizado ou zoom óptico.

## Formatos e conexão observados

Fonte primária: `v4l2-ctl -d /dev/video0 --list-formats-ext` e `/sys/class/video4linux/video0/device/../speed`.

- USB negociado: **480 Mbit/s**, conexão High-Speed, não SuperSpeed.
- Formatos: **YUYV** e **MJPG**.
- Resoluções enumeradas em ambos: 176×144, 320×240, 424×240, 640×360, 640×480, 848×480, 960×540, 1280×720, 1600×896 e 1920×1080.
- MJPG: até **30 fps**, inclusive em 1920×1080.
- YUYV: até 30 fps até 848×480; 15 fps em 960×540; 10 fps em 1280×720; 7,5 fps em 1600×896; 5 fps em 1920×1080.
- **60 fps não foi anunciado pelo dispositivo na conexão atual.**

A documentação Logitech menciona limite de 720p30 via USB 2.0 no contexto Capture; a enumeração Linux local oferece MJPG1080p30. A disponibilidade real deve vir do driver, mantendo as duas observações distintas. Trocar para uma conexão SuperSpeed direta e enumerar novamente é a recomendação para investigar 60 fps; isso não foi testado nesta pesquisa.

## Limites e decisões de implementação

O kernel define os controles disponíveis como propriedades do dispositivo, compartilhadas entre aplicações; outro programa pode alterá-las. Recomenda-se atualizar a leitura ao abrir o painel e após escrever um controle. Fonte: [controles de usuário V4L2](https://docs.kernel.org/userspace-api/media/v4l/control.html).

Não foram enumerados controles de rotação, espelhamento, HDR, LED, privacidade, seguimento facial ou enquadramento automático. A Logitech anuncia recursos extras em conjunto com Capture; não há nesta pesquisa comprovação de uma API Linux para esses recursos. O plugin deve expor os 17 controles observados e descobrir eventuais variações, sem criar opções fictícias. O áudio pertence à pilha de áudio do sistema e não apareceu nesta interface V4L2.

Resolução, formato e FPS devem ser consultáveis como capacidades. Configurá-los em um painel não garante o formato que OBS, navegador ou outro consumidor negociará posteriormente. Presets de imagem podem salvar os controles; restaurar valores manuais requer tratar primeiro o modo automático e reler as dependências.

Para executar `v4l2-ctl`, usar argumentos separados, sem interpolação em shell, conferir códigos de saída e mostrar erros de desconexão/permissão. Enumerar somente nós de captura da StreamCam evita confundir o nó de metadados com a câmera.

## Prévia solicitada durante a implementação

O Qt Multimedia permite enumerar as câmeras com `MediaDevices` e ligá-las a `Camera` → `CaptureSession` → `VideoOutput`. Não é necessário adicionar `AudioInput`, `MediaRecorder` ou `ImageCapture` para visualizar vídeo. O plugin carrega esse componente somente ao ativar a prévia e o destrói ao fechar o painel. Fontes: [Camera](https://doc.qt.io/qt-6/qml-qtmultimedia-camera.html), [CaptureSession](https://doc.qt.io/qt-6/qml-qtmultimedia-capturesession.html), [VideoOutput](https://doc.qt.io/qt-6/qml-qtmultimedia-videooutput.html).

Na máquina testada, o ID Qt da StreamCam corresponde a `/dev/video0`, permitindo escolher o mesmo nó que o helper V4L2 usa. Essa correspondência é específica do backend Linux; o plugin recusa usar outra câmera como fallback. A prévia recebeu frames no teste real, encerrou a captura ao fechar e permaneceu desligada após reabrir. A enumeração de controles continuou disponível durante a prévia.
