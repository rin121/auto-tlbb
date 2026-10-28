# Test case — Phiêu Miểu Phong & Thập Nhị Sát Tinh

## Chạy test tự động (logic, không cần game)

Từ thư mục `AutoHoc`:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

| File | Phạm vi |
|------|---------|
| `tests/test_pho_ban_pmp.py` | Bộ đếm ngày, PMP Sơ / thường, thông báo hết lượt, map (kể cả Lâu Lan), gom đội, tập hợp, về thành, kẹt ải, ải 2 boss ẩn thân (PMP-T05), xoay vòng (chặn vòng mới qua 0h — XV-03, `can_di`, xóa cờ xoay vòng) |
| `tests/test_sat_tinh.py` | Lượt Sát Tinh, chuyển PMP → Sát Tinh, parse hội thoại NPC (hết lượt, còn lại, mã màu), bước vào lôi đài, phát hiện Sát Tinh ra |
| `tests/test_giao_dich_ngay.py` | Nút Giao dịch ngay (XV-06/07, GD-01/02): có / không xoay vòng, chia nhóm theo nhóm game, tạm dừng / bật lại auto giữ bộ đếm, đội viên giao cho trưởng nhóm |
| `tests/test_cau_hinh_toi_uu.py` | Sao chép cấu hình nhanh, ghi `cau_hinh.json` một lần, bản cũ không ghi đè bản mới |
| `tests/test_nhom_online.py` | Nút Test nhóm online (XV-09): chọn nhân vật đang trong game, trưởng PT lên đầu, bỏ acc chính / train, tối đa 6; chạy 1 round không đăng nhập |
| `tests/test_ghi_pmp.py` | Công cụ ghi hành động chơi tay `cong_cu/ghi_pmp.py` (đọc trạng thái, hội thoại NPC) |
| `tests/test_tu_duyet.py` | Tự duyệt popup không bao giờ bấm hộp thoát game "Các hạ quyết rời bỏ thế giới…" (đang PMP / Sát Tinh không bị văng client); hộp thường, hộp ngân lượng vẫn duyệt |
| `tests/test_nang_cap_nhan_vat.py` | Nâng cấp nhân vật (NC-01..05): file `nang_cap_da_xong.json` (xong / làm dở theo bước), Bách Bảo 9 sao có mới làm bước 1, Hoàng Kim bỏ món đã mang, danh sách đồ cũ để vứt, món shop chỉ mua khi đã có giá Điểm Tặng, nội lực max 250.000.000 thì không cộng; công cụ ghi `cong_cu/ghi_thao_tac.py` |

Bắt buộc chạy lại sau **mỗi lần sửa code `.py`** (rule `.cursor/rules/autohoc-pmp-sat-tinh-tests.mdc`).

---

## Kiểm thử thủ công trong game (checklist)

Điều kiện chung: tab **Phó bản** bật **Đi PMP**, tab **Xoay vòng** bật **Bắt đầu** (nếu test theo luồng xoay vòng). Ghi log `nhat_ky_auto.log`.

### PMP — một nhân vật

| ID | Bước | Kỳ vọng |
|----|------|---------|
| PMP-01 | Map lạ, bật auto PMP | Tự về Đại Lý (F / kỹ năng về thành) |
| PMP-01c | Ở Đại Lý chạy tới NPC Di Chuyển 90 giây mà không mở được hội thoại (kẹt đường) | Log «không mở được hội thoại Di Chuyển…, dùng kỹ năng Về thành Đại Lý rồi thử lại», dùng Về thành rồi chạy lại tới Di Chuyển; không nghỉ 5 phút (chỉ báo lỗi khi kẹt cả 3 lần) |
| ST-LD | Sát Tinh: NPC đã đưa cả đội vào Lôi đài sinh tử nhưng game đổi map chậm (luồng còn gom ở Lạc Dương) | Log «Sát Tinh đội đã vào Lôi đài sinh tử, dắt đội tới chỗ đánh», đội trưởng dẫn đội tới giữa lôi đài và đánh bình thường; không còn lỗi «đội trưởng đang ở [Lôi đài sinh tử], không phải Lạc Dương» |
| PMP-01b | Nhân vật bị «Thân thể bị quản chế» (buff Buff0_16 «Không thể sử dụng bất kỳ chiêu thức nào», đứng yên còn mãi) cần về thành | Log «thân thể bị quản chế, di chuyển cho hết…», nhân vật chạy vài bước, «đã hết quản chế», rồi dùng Về thành về Đại Lý |
| PMP-02 | Đại Lý, HP &lt; 50% | Tới NPC Di Chuyển, hồi máu, đóng Quest |
| PMP-03 | Đại Lý → Lạc Dương | Di Chuyển → Bản đồ thành → Lạc Dương |
| PMP-04 | Lạc Dương → PMP | Trịnh Thanh Sương → vào ải, đánh 4 ải + boss |
| PMP-05 | Xong 1 vòng | Log tăng `so_vong` hôm nay; về thành / tiếp vòng theo cấu hình |
| PMP-06 | Hết lượt PMP (game báo) | `het_luot` = true; không vào PMP thường nữa |

### PMP — tổ đội

| ID | Bước | Kỳ vọng |
|----|------|---------|
| PMP-T01 | Trưởng + 2 đội viên, bật tổ đội | Đội viên tự Đại Lý → Lạc Dương → gần NPC PMP |
| PMP-T02 | Trưởng vào ải | Đội viên theo / vào ải; trưởng `truong_khong_danh` chỉ dẫn đường (nếu bật) |
| PMP-T03 | Trưởng hết lượt, đội viên kẹt trong ải | Đội viên tự về thành (log “kẹt ải” / hết lượt) |
| PMP-T04 | Đội viên đánh quá 120s chưa chết quái ải | Lần 2: trưởng xuống thú đánh cùng; vẫn quá 120s → cả đội về Đại Lý chạy vòng mới (tối đa 5 lần), không nghỉ 5 phút trong ải |
| PMP-T05 | Ải 2 Tang Thổ Công ẩn thân giữa trận (server tăng máu boss) | Log «Tang Thổ Công ẩn thân (còn x% máu), cả đội đứng chờ hiện lại»: cả đội đứng ở điểm đánh, **không đánh** (kể cả Bích lân cương thi); boss hiện lại → log «hiện lại, đánh tiếp»; lặp tới khi boss chết (~2 phút) rồi mới sang ải 3. Không bị «đã giết» sớm khi boss còn máu, không bị về Đại Lý vì quá 120s |

### Sát Tinh — sau PMP

| ID | Bước | Kỳ vọng |
|----|------|---------|
| ST-01 | Hết lượt PMP, bật “Hết PMP thì Sát Tinh” | NPC đích Lạc Dương: **SÁT TINH** (không còn Trịnh Thanh Sương cho lượt PMP) |
| ST-02 | Hội thoại SÁT TINH | Chọn khiêu chiến → map **Lôi đài sinh tử** |
| ST-03 | Trong lôi đài | Chạy giữa (25,32), đánh Sát Tinh; thông báo hoàn thành → về Lạc Dương/Đại Lý |
| ST-04 | Giữa các vòng ST | Đội viên đứng gần `XY_CHO_SAT_TINH` (154,194) |
| ST-05 | NPC báo hết 20 lượt / ngày mai | Log hết Sát Tinh; `st_het` = true |

### Chỉ Sát Tinh / xoay vòng

| ID | Bước | Kỳ vọng |
|----|------|---------|
| ST-C01 | Bật **Chỉ đi Sát Tinh** | Không vào PMP; NPC Lạc Dương luôn SÁT TINH |
| XV-01 | Xoay vòng 4 acc, 2 round | Mỗi round: PMP (nếu còn) → ST tới hết lượt; đổi nhóm theo cấu hình |
| XV-02 | **Chế độ test** | 1 round, 1 lượt PMP hoặc 1 lượt ST (tùy chỉ Sát Tinh) |
| XV-05 | NPC SÁT TINH báo «Trong tổ đội của các hạ có A, B đã tham gia phụ bản 20 lần trong ngày hôm nay!» | Cả nhóm đánh dấu hết lượt Sát Tinh, giao dịch rồi xoay vòng đăng nhập nhóm / round tiếp theo |
| XV-03 | Qua 0h khi nhóm **đang trong** PMP / Lôi đài | Đi nốt vòng đó, không vào vòng mới; ra khỏi phó bản → tắt auto, giao dịch, làm mới danh sách, chạy lại từ nhóm 1 |
| XV-04 | Qua 0h khi nhóm **chưa vào** phó bản (đang ở Đại Lý / Lạc Dương) | Dừng ngay trong ~3 giây, làm mới danh sách, chạy lại từ nhóm 1 |
| XV-06 | Nhóm đang đi PMP / Sát Tinh, bấm **Giao dịch ngay** | Trong ~3–6 giây cả đội tắt auto, đội viên chạy tới trưởng nhóm giao đồ mới nhặt (từ đầu round); xong bật lại Auto + Phó bản, bộ đếm hôm nay giữ nguyên, đi tiếp |
| XV-07 | Xoay vòng **đang chạy** nhưng đang đăng nhập / lập nhóm, bấm **Giao dịch ngay** | Báo bấm lại sau, không làm gì |
| XV-08 | Nhóm kẹt (đang đi PMP / Sát Tinh hoặc chờ lập nhóm mãi), bấm **Nhóm tiếp theo** → Có | Đang phó bản: tắt auto, về Đại Lý (hoặc ở lại Lạc Dương), log đủ / thiếu thành viên, đội viên còn trong game giao đồ cho trưởng, rồi sang round / nhóm kế tiếp. Đang chờ lập nhóm: bỏ round, sang round / nhóm kế tiếp |
| XV-09 | Xoay vòng **không** chạy; 2–6 nhân vật đã trong game (có hoặc chưa cùng PT), bấm **Test nhóm online** → Có | Hộp xác nhận liệt kê đúng các nhân vật đang online (không có acc chính / acc train), trưởng nhóm = trưởng PT trong game (chưa PT thì tài khoản số nhỏ nhất). Không đăng xuất / đăng nhập lại ai; lập nhóm, đi 1 lượt PMP (bật «Chỉ Sát Tinh» thì 1 lượt Sát Tinh), về thành, giao dịch (nếu bật) rồi dừng, game vẫn mở; tiến trình xoay vòng đã lưu không bị đổi |
| XV-10 | Xoay vòng đang đi phó bản (vd. nhóm 3 round 2, đang ở step 3 PMP) → **Dừng** → **Bắt đầu** lại | Log «Nhóm đang trong game còn lượt: … (round 2) — đi tiếp, không đăng xuất / đăng nhập lại»; không ai bị về chọn máy chủ; các nhân vật log «Đã vào game nhân vật …, bỏ qua đăng nhập»; đội trưởng log «đang trong [Phiêu Miểu Phong], đi tiếp step đang dở» và «đang trong phó bản ở step 3/5 …», đi tiếp từ step 3 (không về thành). Đang trong Lôi đài sinh tử thì đánh nốt Sát Tinh |
| XV-11 | Nhóm đang online đã hết lượt hôm nay → Bắt đầu lại | Không ưu tiên nhóm đó; đi nhóm / round kế tiếp theo tiến trình đã lưu |
| GD-01 | **Không** bật xoay vòng; trưởng + đội viên cùng nhóm game, đều đang trong auto (vd. đang đi PMP), bấm **Giao dịch ngay** | Tạm tắt auto cả nhóm, đội viên chạy tới trưởng giao đồ mới nhặt (so với túi lúc auto thấy nhân vật vào game), xong bật lại auto / phó bản như cũ |
| GD-02 | Không bật xoay vòng, không có nhóm nào (hoặc trưởng nhóm không có trong auto) | Log «Không có đội viên nào đang cùng nhóm…», không tắt auto ai |

### Nâng cấp nhân vật (tự chạy khi đăng nhập; nút test ở tab Tạo nhân vật)

| ID | Bước | Kỳ vọng |
|----|------|---------|
| NC-01 | Nhân vật chưa có trong `nang_cap_da_xong.json`, túi có Bách Bảo Nang / Rương 9 sao, bấm **Test nâng cấp NV** | Xếp túi, tháo bộ Bách Bảo thường, mang bộ 9 sao; mua Minh Tôn (Thần Khí Tân Thủ) + Nga Mi Biến Dị, mang thần khí, dùng trứng; nhập 4 giftcode ở NPC GIFTCODE; mang 10 món Hoàng Kim, vứt đồ Tân Thủ / Thanh Đồng Đao / Bách Bảo thường, dùng hết Hộp Point; rút 2 lần 10.000.000 Nội Lực; cộng 10.000.000 Nội Lực rồi hết điểm vào Thân Pháp. Log «đã nâng cấp xong», tên được ghi vào file |
| NC-02 | Túi **không** có Bách Bảo 9 sao (đã vứt) | Log «bỏ qua bước 1», các bước sau vẫn làm |
| NC-03 | Nội lực (Alt+C) đã ≥ 250.000.000 | Không cộng Nội Lực, log «Nội lực đã max», cộng hết vào Thân Pháp |
| NC-04 | Dừng / lỗi giữa chừng rồi chạy lại | Bỏ qua các bước đã xong (không mua trứng / rút điểm lần nữa) |
| NC-05 | Nhân vật đã có trong file | Nút test log «đã nâng cấp từ trước, bỏ qua»; đăng nhập lại không nâng cấp nữa |
| NC-06 | Đăng nhập (tab Tài khoản hoặc xoay vòng) nhân vật chưa có trong file | Vào game xong, trạng thái «Nâng cấp…», làm 6 bước rồi mới báo «Đã vào game»; lỗi giữa chừng chỉ ghi log «lần đăng nhập sau làm tiếp», vẫn tính là đăng nhập được |
| NC-07 | Tạo nhân vật mới (tab Tạo nhân vật / xoay vòng tạo round) | Nhận đồ tân thủ xong thì nâng cấp luôn rồi mới về chọn máy chủ |
| NC-08 | Nhân vật chưa nâng cấp đang đứng ở map khác Đại Lý (Lạc Dương, Tô Châu…) | Log «đang ở [map], về Đại Lý trước khi nâng cấp», dùng kỹ năng Quay về Đại Lý thành rồi mới làm bước 1; đang ở Đại Lý thì làm luôn |
| NC-09 | Chạy trên máy ảo Win7 (lag) | Mang Bách Bảo 9 sao / thần khí / 10 Hoàng Kim không sót món nào (log «chưa mang được … (lần k/3)» rồi «đã mang»); mua, dùng trứng, giftcode, rút / cộng điểm không bị làm 2 lần do game trả lời trễ; còn sót thì bước đó báo lỗi, lần đăng nhập sau làm tiếp |

### Cài đặt & file

| ID | Bước | Kỳ vọng |
|----|------|---------|
| CFG-01 | Bật giảm đồ họa, mở game mới | `System.cfg` / `.pfc` View_* thấp; trong game log giảm đồ họa |
| CFG-02 | Sang ngày mới (hoặc xóa đếm) | `hom_nay` reset `so_vong`, `st_vong`, cờ hết lượt |

---

## Ghi chú regression

- `UnboundLocalError: bay_gio` trong `theo_doi_pmp`: đã sửa — nếu tái hiện, chạy unittest và grep log.
- Client Nhất Kiếm: nút **Duyệt** Thiết lập hiển thị có thể không lưu hết slider; auto ghi trực tiếp qua Lua + file profile.
