# trailing-stop-strategy — 專案說明(給 Claude Code 讀)

「大叔美股筆記」12 問美股研究站。純靜態 HTML + GitHub Pages,無建置步驟。
線上網址:https://jimmychou1023.github.io/trailing-stop-strategy/stocks.html

## 結構

```
stocks.html              類股總覽(首頁)
assets/report.css        共用樣式(單一來源;個股頁用 ../assets/report.css,根目錄頁用 assets/report.css)
data/coverage.json       涵蓋清單:每檔 ticker / file / rr / verdict / position / next_earnings。改資料要同步更新這份
_template-report.html    新個股範本(含 {{TICKER_LC}} 等佔位符;複製進類股資料夾後替換)
ai-optics/    index.html(類股首頁)· compare-report.html(對照表)· {aeva,cohr,lite,mrvl,avgo}-report.html
chip-ip/      index.html · compare-report.html · {ceva,aip,rmbs,arm}-report.html
```

- 每檔個股頁都嵌 TradingView mini-symbol-overview widget(即時圖,唯一即時來源)。
- 目前涵蓋:**AI 光學/互連**(COHR / AEVA / AVGO / MRVL / LITE)、**半導體 IP**(CEVA / AIP / RMBS / ARM)。

## 核心計算規則(不要偏離)

- **三情境估值**:每檔固定 Bear / Base / Bull 三個合理價與機率(通常 30/40/30 或 25/50/25)。
- **加權合理價** = Σ(情境價 × 機率)。
- **預期差** = (加權合理價 − 現價) ÷ 現價。
- **報酬風險比(報酬÷風險)** = (Bull − 現價) ÷ (現價 − Bear)。**數字越大越有利**(是「上檔÷下檔」,不是「賠率」)。
- **只有出現新財報 / 重大新聞才調整情境或論點**;否則情境固定,只依「現價」重算預期差與報酬風險比。
- 報酬風險比越高排越前面;類股首頁與 compare 都要**依 rr 重新排序**。

## 改一檔價格 = 要同步這幾處

1. 個股頁 `<sector>/<ticker>-report.html`:banner、基本資料快照(股價/市值/日期)、chartnote 日期、Expectations、三情境校準註記、result 區(股價/預期差/報酬風險比)、怎麼讀結果 callout、風險提醒收盤價、footer 日期。
2. 該類股 `compare-report.html`:表格該欄(股價/市值/預期差/報酬風險比/結論)、rank 排序句、結論卡、asof/footer 日期。
3. 該類股 `index.html`:個股卡(rr badge / 內文 / 排序 #)、asof/footer 日期、note。
4. `data/coverage.json`:該檔 `rr` / `verdict`、頂層 `updated`。
5. `stocks.html`:總覽日期(若整體基準日更新)。

改完務必:`python3 -m json.tool data/coverage.json` 驗證 JSON;grep 舊價/舊日期確認無殘留;檢查相對連結。

## 股價資料來源(重要)

- 價位、機率、部位皆為**研究流程示意,非投資建議**;頁面已註明。
- **本機環境可直接連網**,請用結構化來源抓收盤價(不要用網頁搜尋摘要——它會混日期、不可靠)。例如:
  - Stooq EOD CSV(免金鑰):`curl -s "https://stooq.com/q/l/?s=cohr.us&f=sd2t2ohlcv&e=csv"`
  - 或 Python `yfinance`。
- 抓到的價**要標明是哪一交易日的收盤**;抓不到就說抓不到,不要猜。
- 使用者若直接提供收盤價,以使用者提供的為準。

## 最新狀態

- 最新基準日 **2026/08/21(週五)收盤**。
- AI 光學/互連 報酬風險比排序:COHR 6.34 > AEVA 2.98 > AVGO 1.71 > MRVL 1.41 > LITE 1.09。
- 半導體 IP 排序:CEVA 2.84 > AIP 2.68 > RMBS 2.53 > ARM 2.47。
- 8/21 收盤:COHR 289.52 / AEVA 18.29 / AVGO 368.45 / MRVL 237.04 / LITE 866.71 / CEVA 27.99 / AIP 23.89 / RMBS 91.24 / ARM 243.32。

## Git

- GitHub 僅作推播 + Pages 部署。改完 commit → push,Pages 自動重新部署。
- commit / PR 內文不要寫入任何模型名稱。
