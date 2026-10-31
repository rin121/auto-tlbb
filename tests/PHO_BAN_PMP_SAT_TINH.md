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
| `tests/test_thieu_nhan_vat.py` | XV-21: màn chọn nhân vật không có nhân vật round → báo thiếu (danh sách trống chờ 8 giây); đồng bộ sổ «đã tạo» theo danh sách thật; xoay vòng tạo lại rồi đăng nhập lại |
| `tests/test_nhom_online.py` | Nút Test nhóm online (XV-09): chọn nhân vật đang trong game, trưởng PT lên đầu, bỏ acc chính / train, tối đa 6; chạy 1 round không đăng nhập |
| `tests/test_ghi_pmp.py` | Công cụ ghi hành động chơi tay `cong_cu/ghi_pmp.py` (đọc trạng thái, hội thoại NPC) |
| `tests/test_tu_duyet.py` | Tự duyệt mọi hộp, kể cả hộp thoát game "Các hạ quyết rời bỏ thế giới…" (người dùng chọn duyệt tất cả, 29/10/2026); hộp thường, hộp ngân lượng duyệt |
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
| XV-14 | Xoay vòng: một nhóm đăng nhập lỗi (mã kiểm tra lỗi, game treo ở chọn nhân vật…) | Log «Bỏ tài khoản …» rồi «Round k: xếp lại cuối hàng chờ để đăng nhập lại sau …»; các nhóm sau đi tiếp, tới cuối hàng thì đăng nhập lại acc đó; lỗi quá 2 lần / acc×round thì «đã thử lại 2 lần vẫn đăng nhập lỗi, bỏ hôm nay»; dừng / mở lại app vẫn nhớ số lần |
| GA-01 | Mở GAuto_2025 + đăng nhập đội trưởng; AutoHoc **không** Admin, bấm «Test GAuto» | Log «quyền: GAuto Admin, AutoHoc thường», hỏi mở lại AutoHoc quyền Admin; Có → hộp UAC, AutoHoc mở lại quyền Admin |
| GA-02 | AutoHoc Admin, «Test GAuto», nhập tên đội trưởng, chọn Có (tích thử) | Log từng bước: thấy cửa sổ, bảng nhân vật, chọn đúng dòng, tự mở tab Nhiệm vụ, trạng thái 5 ô khung Ác Tặc, map GAuto (cảnh báo map ☑ AutoHoc mà GAuto không có, vd Tây Hồ); ô Map GAuto đổi sang map đầu ☑ AutoHoc (chuột tự bấm ~1 giây rồi trả về chỗ cũ); ô «Ác Tặc» tích 3 giây rồi trả lại; dòng cuối «OK» |
| GA-03 | Bật «Đi Ác Tặc qua GAuto», để Kiếm Các đầu danh sách ☑, tới khung giờ | AutoHoc đưa đội tới Kiếm Các, rồi chọn map Kiếm Các trên GAuto cho dòng đội trưởng và tích Ác Tặc; hết «Phút / khung» thì bỏ tích Ác Tặc trên GAuto, đội đi tiếp phó bản (xoay vòng) |
| TD-01 | Bật «Tự duyệt popup», mở vài game; bấm X từng cửa sổ, hoặc chuột phải icon game ở taskbar → «Đóng tất cả cửa sổ» | Mọi game tự bấm Duyệt hộp «rời bỏ thế giới» và tắt trong ~1–2 giây, log «Tự duyệt [MessageBox_Self]: Các hạ quyết rời bỏ thế giới…» |
| GA-04 | Xoay vòng 4 acc cùng login trong GAuto (vd caychay244 trưởng, 255/266/277 đội viên), dòng đang chọn trên GAuto là đội viên, khung Ác Tặc GAuto thu gọn; tới khung giờ Ác Tặc | AutoHoc **không** chọn / bấm dòng đội viên nào; GAuto chuyển sang dòng đội trưởng (tab đầu GAuto ghi đúng tên đội trưởng, có lúc chuột tự bấm vào dòng ~1 giây), khung Ác Tặc tự mở rộng, chọn map AutoHoc rồi tích Ác Tặc **chỉ** cho đội trưởng. GAuto đổi sang nhân vật khác giữa chừng thì báo lỗi, không tích nhầm |
| GA-06 | Bảng nhân vật GAuto có trưởng nhóm (vd caychay32) + đội viên, ô đầu dòng trưởng nhóm đang bỏ tích; khung Ác Tặc GAuto, đội tới map | Chỉ dòng trưởng nhóm bị bấm: log «tích ô đầu dòng «caychay32» (bật auto GAuto)», chờ ~5 giây, rồi chọn dòng, map, tích «Ác Tặc» **đúng 1 lần** — dòng đội viên không đổi gì. Lỗi giữa chừng: log «… — không thử lại khung này, kiểm tra GAuto», không bấm lặp. PT vỡ giữa chừng: đội viên hiện «chờ vào PT của caychay32», không đụng GAuto. Hết N phút (config «phút GAuto»): bỏ tích ô đầu dòng (nếu AutoHoc đã tự tích) rồi bỏ tích «Ác Tặc» 1 lần |
| GA-05 | Mở AutoHoc.exe bản mới (hiện hộp UAC → Có); khung Ác Tặc GAuto, đội tới map, GAuto gặp Ác Tặc khiêu chiến → cả đội vào «Tặc Khấu doanh địa» | **Không** có log «GAuto đang chạy quyền Admin … AutoHoc thì không»; log «đã tới Kiếm Các, bật GAuto tới HH:MM». Trong Tặc Khấu doanh địa: trạng thái «Ác Tặc (GAuto): đang đánh trong [Tặc Khấu doanh địa]», **không** có «Ác Tặc — đã về Đại Lý» / «nhóm chưa đúng (trưởng PT X, cần X)». Hết khung (kể cả đang trong phó bản): bỏ tích Ác Tặc GAuto ngay, log «hết khung HH:MM-HH:MM, tắt Ác Tặc GAuto», cả đội về Đại Lý đi tiếp xoay vòng phó bản |
| GA-08 | Khung Ác Tặc GAuto, ô đầu dòng trưởng nhóm đang bỏ tích, đội đứng ở map chỉ định lúc giờ bắt đầu | Các ô khung Ác Tặc (kể cả «Ác Tặc») được bấm bằng **chuột thật** (con trỏ nhảy tới ô rồi trả về); ngay sau đó GAuto đi tìm Ác Tặc / khiêu chiến **không cần tích tay lại**. GAuto nạp lại cài đặt muộn làm mất ô: log «GAuto nạp lại cài đặt xóa ô «Ác Tặc», tích lại» đúng 1 lần, ô cuối cùng ☑ |
| GA-09 | Nhóm đang ở Lạc Dương (vừa PMP / Sát Tinh) khi tới khung Ác Tặc; lần 1 map đầu ☑ là Tung Sơn (hoặc Đôn Hoàng), lần 2 là Kiếm Các (hoặc Vô Lượng Sơn) | Tung Sơn / Đôn Hoàng: log «đang ở Lạc Dương, đi thẳng Tung Sơn (không về Đại Lý)», triệu tập đội tại Lạc Dương rồi chạy ra cổng, **không** dùng Về thành. Kiếm Các / Vô Lượng Sơn: vẫn «đã về Đại Lý», gom đội ở Đại Lý rồi đi NPC Di Chuyển như cũ |
| GA-07 | «Phút GAuto» = 20, khung 21h, xoay vòng đang chạy nhóm A; giữa khung nhóm B login (round / nhóm sau) | 20:57 chưa đi; **20:58** nhóm A ra map chỉ định, tới map trước 21:00 thì trạng thái «đã tới X, chờ …s tới giờ bật GAuto»; **21:00** tích Ác Tặc GAuto (log «bật GAuto tới 21:20»); **21:20** bỏ tích, đội về đi tiếp phó bản. Nhóm B login lúc 21:05: log «khung 21:00-21:20 đã do nhóm A đi — nhóm này tiếp tục phó bản», **không** ra map / không đụng GAuto |
| XV-15 | Giao dịch cho acc chính, chọn «Tất cả acc phó bản»; một tài khoản (không phải trưởng nhóm) có 3 nhân vật **chưa có trong sổ túi đồ**, nhân vật đầu không có đồ | Log «… không có đồ» ở nhân vật đầu, rồi 2 nhân vật còn lại: «nhân vật khác của … không có đồ (đã giao cho trưởng nhóm), bỏ qua không đăng nhập»; đi tiếp sang tài khoản sau. Nhân vật trưởng nhóm (trưởng mỗi round / trưởng bù) và nhân vật sổ ghi còn đồ / chưa rõ vẫn được đăng nhập kiểm tra |
| XV-16 | Xoay vòng xong một round (có đội viên giao lỗi, đồ còn trong túi) | `so_tui_do.json` cạnh exe: cả nhóm «da_ghi» + số ô; log «sổ túi đồ ghi còn đồ giao cho acc chính: …» liệt kê trưởng nhóm và đội viên giao lỗi. Dừng giữa round thì nhóm đó còn «chua_ro» |
| XV-17 | Sau XV-16, Giao dịch cho acc chính (chế độ trưởng nhóm hoặc tất cả) | Log «Bỏ qua … (sổ túi đồ ghi không có đồ)» và «Thêm … nhân vật sổ túi đồ ghi còn đồ: …» (đội viên giao lỗi được đăng nhập dù không phải trưởng nhóm). Giao xong, sổ ghi `so_o` 0, `da_giao_acc_chinh` true; bấm Bắt đầu lại không đăng nhập lại nhân vật đó. Đi round mới có đồ thì lần giao sau lại có tên |
| XV-20 | Đang xoay vòng nhóm giữa danh sách (vd caychay244–277 round 2), để qua 0h; hoặc bấm «Làm mới danh sách» / «Chạy lại từ đầu» | Log «… Bắt đầu từ tài khoản đầu tiên …» rồi «Nhóm 1 round 1: ghép caychay14, caychay16, …» — **không** có «Nhóm đang trong game còn lượt … đi tiếp». Bấm Dừng rồi «Bắt đầu» thường thì vẫn giữ nhóm đang online đi tiếp |
| XV-21 | Tài khoản (vd caychay30) sổ ghi đã tạo caychay30/300/3000 nhưng trong game không còn nhân vật nào; xoay vòng tới tài khoản đó | Sau ~8 giây ở màn chọn nhân vật: log «Dừng: tài khoản không có nhân vật "caychay30" … — cần tạo nhân vật» → «caychay30: không có nhân vật caychay30 … — tạo caychay30 + nhận đồ tân thủ» → «Sổ ghi đã tạo … nhưng tài khoản không còn, tạo lại + nhận đồ tân thủ» → tạo + nhận đồ → đăng nhập lại vào caychay30 đi round. **Không** còn «Kẹt ở bước chọn nhân vật quá 60 giây» 3 lần |
| XV-19 | Giao dịch cho acc chính, nhân vật vừa Về thành Đại Lý đứng yên không chạy tới NPC Tân Thủ | Lệnh chạy được gửi lại mỗi 5 giây tới khi tới nơi; quá 90 giây thì log «… chưa tới (160, 166) — vẫn giao dịch (tự chạy lại gần …)», nhân vật chạy lại gần acc chính để giao, **không** dừng cả lượt giao |
| XV-18 | Giao dịch cho acc chính chạy tới «Xong» (có XV tài khoản đang tích, xoay vòng đang dừng) | Log «Xong — tự bắt đầu lại xoay vòng phó bản», nút Xoay vòng thành «Dừng», xoay vòng chạy tiếp. Giao bị «Dừng: …» / «Đã dừng» / «Lỗi» thì **không** tự xoay vòng; không tích XV nào thì chỉ ghi log, không hiện hộp thoại |
| XV-12 | Bấm **Giao dịch ngay** khi đội viên không có đồ mới (so với túi lúc đầu ngày) | Log «… không có đồ mới trong túi, khỏi giao dịch» rồi «không đội viên nào có đồ mới trong túi, bỏ qua»; phó bản / auto **không** bị tạm dừng, không ai chạy tới trưởng nhóm |
| XV-13 | Nhặt đồ trong PMP → Dừng → Bắt đầu lại (hoặc tắt mở app / vào lại game) → Giao dịch ngay | Đồ nhặt trước khi dừng vẫn được tính là đồ mới (ảnh túi gốc trong ngày lưu ở `anh_tui_goc.json`); chỉ đội viên có đồ mới chạy tới giao dịch |
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
| NC-10 | Nâng cấp / nhận đồ tân thủ: tăng point xong ở NPC Cộng Point (góc lag, chạy đi bị giật về) | Đóng hội thoại rồi dùng **Về thành Đại Lý** ngay (chưa đổi chỗ thì thử lại tối đa 3 lần), không chạy bộ khỏi NPC; không ghé NPC Cộng Point thì không Về thành |

### Cài đặt & file

| ID | Bước | Kỳ vọng |
|----|------|---------|
| CFG-01 | Bật giảm đồ họa, mở game mới | `System.cfg` / `.pfc` View_* thấp; trong game log giảm đồ họa |
| CFG-02 | Sang ngày mới (hoặc xóa đếm) | `hom_nay` reset `so_vong`, `st_vong`, cờ hết lượt |

---

## Ghi chú regression

- `UnboundLocalError: bay_gio` trong `theo_doi_pmp`: đã sửa — nếu tái hiện, chạy unittest và grep log.
- Client Nhất Kiếm: nút **Duyệt** Thiết lập hiển thị có thể không lưu hết slider; auto ghi trực tiếp qua Lua + file profile.
