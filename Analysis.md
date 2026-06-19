# Phan tich ket qua lab

## Ket qua benchmark offline

### Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1339 | 13646 | 0.000 | 0.600 | 0 | 0 |
| Advanced | 4629 | 69935 | 0.714 | 0.886 | 2348 | 1 |

### Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 2957 | 38603 | 0.000 | 0.600 | 0 | 0 |
| Advanced | 764 | 16377 | 1.000 | 1.000 | 2274 | 21 |

## Nhan xet

Advanced co recall tot hon baseline vi no tach thong tin on dinh cua nguoi dung ra `User.md`. Khi sang thread moi, baseline chi co short-term memory trong thread hien tai nen khong nhac lai duoc fact cu, con advanced doc profile va tra loi duoc cac cau hoi ve ten, nghe nghiep, noi o, style tra loi va so thich.

O hoi thoai ngan, advanced co the ton hon baseline vi moi luot phai keo them profile memory va quan ly compact context. Day la trade-off hop ly: chi phi prompt tang de doi lay kha nang nho dai han va recall tot hon.

O stress benchmark, compact memory giup advanced giam manh `Prompt tokens processed`. Baseline tiep tuc mang lich su day du trong thread nen prompt cost tang nhanh, con advanced chi giu summary ngan va mot so message gan nhat. Vi vay compact khong toi uu chu yeu o token sinh ra cua agent, ma toi uu phan ngu canh phai xu ly lai qua nhieu luot.

`Memory growth (bytes)` cua advanced tang vi `User.md` luu cac fact on dinh va metadata cho confidence, turn, mentions, source. Neu he thong chay lau, file memory co rui ro phinh to hoac luu sai fact neu extraction qua de dai.

## Bonus 90-100

Phan bonus da duoc them truc tiep vao `memory_store.py` va duoc kiem chung trong `test_agents.py`.

- Confidence threshold: `ProfileUpdate` co `confidence`; `UserProfileStore.upsert_fact()` chi ghi fact khi confidence >= 0.70. Cac cau mo ho nhu "co the", "hinh nhu", "chac la" bi ha confidence va khong ghi vao `User.md`.
- Entity extraction co cau truc: facts duoc tach thanh field ro rang nhu `Name`, `Location`, `Profession`, `Response style`, `Favorite drink`, `Favorite food`, `Pet`, `Interests`. Moi fact co metadata `confidence`, `updated_at`, `last_seen`, `mentions`, `source`.
- Conflict handling: khi fact moi thay the fact cu, `upsert_fact()` cap nhat gia tri hien hanh va them muc vao `Conflict history`. Vi du noi o co the duoc sua tu Hue sang Da Nang ma khong giu dong thoi hai fact hien hanh.
- Memory decay: `StoredFact.decayed_confidence()` va `decay_report()` tinh do uu tien cua fact theo thoi gian/so lan nhac lai. Decay duoc dung nhu tin hieu uu tien, khong xoa fact da du confidence de tranh lam giam recall qua som.

Rui ro cua bonus la `User.md` lon hon do them metadata va conflict history. Doi lai, reviewer co the thay ro vi sao fact duoc ghi, fact nao bi thay the, va do tin cay cua memory thay doi ra sao.

## Bang chung cho muc 100

Phan bonus khong chi co code ma co test va demo rieng:

- `test_bonus_confidence_threshold_skips_uncertain_facts`: chung minh cau mo ho/cau hoi khong lam ban memory.
- `test_bonus_conflict_handling_updates_corrected_fact`: chung minh correction thay fact cu va ghi conflict history.
- `test_bonus_structured_metadata_and_decay_report`: chung minh fact co metadata va decay score.
- `test_bonus_noise_does_not_overwrite_stable_profession`: chung minh cau dua ve nghe nghiep khong overwrite stable profession.
- `test_bonus_corrected_location_recall_uses_latest_fact`: chung minh recall thread moi dung fact moi, khong tra fact cu.
- `test_bonus_repeated_mentions_increase_fact_mentions`: chung minh lap lai fact tang `mentions` thay vi tao duplicate.

Script `src/demo_memory_profile.py` tao mot profile mau va in ra:

- `User.md` voi stable facts co metadata.
- `Conflict history` khi noi o duoc sua.
- `Decay report` cho tung fact.
- Cau tra loi cross-session recall dung ten, nghe, noi o moi, va response style.

Tac dong cua bonus:

- Recall tot hon trong truong hop co correction vi fact hien hanh duoc cap nhat co chu dich.
- Memory an toan hon vi cau hoi/cau dua/cau mo ho khong du confidence de ghi vao `User.md`.
- Reviewer de audit hon vi moi fact co source, confidence va lich su conflict.

Rui ro moi:

- Prompt token trong hoi thoai ngan tang vi `User.md` co them metadata.
- Conflict history can duoc prune trong he thong production neu chay lau.
- Decay chi la heuristic offline, can calibration neu dung cho san pham that.
