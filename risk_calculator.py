import json
from pathlib import Path


FILE_NAME = Path(__file__).with_name("pull_requests.json")
MUC_DO_TIENG_ANH = {"THAP": "LOW", "TRUNG BINH": "MEDIUM", "CAO": "HIGH"}


def tinh_diem_rui_ro(danh_sach_file, so_dong_them, so_dong_xoa):
    diem = 0
    
    # Tinh diem theo so luong file thay doi (moi file 2 diem)
    so_file = len(danh_sach_file)
    diem = diem + (so_file * 2)
    
    # Tu dong quet xem co file nhay cam (.env, config, secret) hay khong
    co_file_nhay_cam = False
    for file in danh_sach_file:
        if ".env" in file or "config" in file or "secret" in file:
            co_file_nhay_cam = True
            break
            
    # Neu co file nhay cam, cong ngay 40 diem rui ro
    if co_file_nhay_cam == True:
        diem = diem + 40
        
    # Tinh diem theo tong so dong code thay doi (them + xoa)
    tong_so_dong = so_dong_them + so_dong_xoa
    if tong_so_dong > 500:
        diem = diem + 25  # Thay doi lon
    elif tong_so_dong > 200:
        diem = diem + 15  # Thay doi trung binh
    else:
        diem = diem + 5   # Thay doi nho
        
    # Xep loai muc do rui ro dua tren tong diem
    if diem >= 50:
        muc_do = "CAO"
    elif diem >= 20:
        muc_do = "TRUNG BINH"
    else:
        muc_do = "THAP"
        
    return diem, muc_do, co_file_nhay_cam


def cap_nhat_rui_ro(pr):
    diem, muc_do, co_file_nhay_cam = tinh_diem_rui_ro(
        pr["danh_sach_file"], pr["so_dong_them"], pr["so_dong_xoa"]
    )
    ket_qua = {
        "so_file_thay_doi": len(pr["danh_sach_file"]),
        "co_chua_file_nhay_cam": co_file_nhay_cam,
        "risk_score": diem,
        "risk_level": MUC_DO_TIENG_ANH[muc_do],
    }
    da_thay_doi = any(pr.get(ten) != gia_tri for ten, gia_tri in ket_qua.items())
    pr.update(ket_qua)
    return da_thay_doi, muc_do


if __name__ == "__main__":
    with FILE_NAME.open("r", encoding="utf-8") as file:
        pull_requests = json.load(file)

    print("=== CHUONG TRINH DANH GIA RUI RO PULL REQUEST ===")
    can_luu = False
    for pr in pull_requests:
        da_thay_doi, muc_do = cap_nhat_rui_ro(pr)
        can_luu = can_luu or da_thay_doi
        print(f"\n[{pr['id']} - {pr['title']}]")
        print(f"- Danh sach file: {pr['danh_sach_file']}")
        print(f"- So dong code them/xoa: +{pr['so_dong_them']} / -{pr['so_dong_xoa']}")
        print(f"- Phat hien file nhay cam: {pr['co_chua_file_nhay_cam']}")
        print(f"- Tong diem rui ro: {pr['risk_score']}")
        print(f"- Danh gia: {muc_do}")

    if can_luu:
        with FILE_NAME.open("w", encoding="utf-8") as file:
            json.dump(pull_requests, file, indent=4, ensure_ascii=False)
