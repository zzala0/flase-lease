import numpy_financial as npf

class LeaseCalculate:
    def __init__(self, frdate, todate, rate, lease_fee, lease_init_fee=0, deposit_amt=0, rstr_alwn_amt=0, prnt_asset=0):
        self.period = self.monthdelta(frdate, todate)

        # 리스 사이클
        lease_cycle = [0]
        # 리스료 테이블
        lease_fee_tab = [0]
        # 리스부채 테이블
        lease_lblt_tab = []
        # 이자비용 테이블
        intr_exp_tab = [0]
        # 보증금 유효이자 테이블
        deposit_intr_tab = [0]
        # 보증금 현할차 테이블
        deposit_dscnt_tab = []
        # 복구충당부채전입액 테이블
        rstr_exp_tab = [0]
        # 복구충당부채 테이블
        rstr_alwn_tab = []
        # 감가상각비 테이블
        depr_exp_tab = [0]
        # 사용권자산 테이블
        lease_asset_tab = [0]
        # 하위 계약에 전달할 사용권자산 차이 테이블
        asset_diff_tab = []

        # 기간 리스 할인율 계산
        npv_rate = (1 + rate) ** (1 / 12) - 1
        pv_rate = (1 + rate) ** (self.period / 12) - 1

        # 보증금 현재가치
        deposit_lst = [0]
        deposit_lst.append(deposit_amt)
        deposit_npv = round(npf.npv(pv_rate, deposit_lst))
        deposit_dscnt = deposit_amt - deposit_npv
        deposit_dscnt_tab.append(deposit_dscnt)

        # 복구충당부채 현재가치
        rstr_alwn_lst = [0]
        rstr_alwn_lst.append(rstr_alwn_amt)
        rstr_alwn = round(npf.npv(pv_rate, rstr_alwn_lst))
        rstr_alwn_tab.append(rstr_alwn)

        # 반복횟수(wiile 사용 변수)
        cycle = 0

        while cycle < self.period:
            cycle = cycle + 1
            lease_cycle.append(cycle)

            # 리스료 테이블 생성
            # NPV를 마지막 지급분부터 쌓아나가므로, 최초 지급금액을 리스트의 마지막에 추가하여 계산한다.
            if cycle == self.period:
                if lease_init_fee == 0:
                    lease_fee_tab.append(lease_fee)
                else:
                    lease_fee_tab.insert(1, lease_init_fee)
            else:
                lease_fee_tab.append(lease_fee)

            # 리스부채 NPV 계산
            # 엑셀NPV는 인자가 1개부터 시작하나, NUMPY에선 시작값이 2개부터라 엑셀과 같은 결과를 얻기 위해선 리스트앞에 빈값이 있어야 한다.
            lease_lblt = round(npf.npv(npv_rate, lease_fee_tab))
            # 리스부채총액 계산 및 테이블 생성
            lease_lblt_tab.append(lease_lblt)

            # # 이자비용 계산 및 테이블 생성
            # pre_idx = cycle - 1
            # cur_idx = cycle - 2
            # if cycle > 1:
            #     intr_exp = lease_fee_tab[pre_idx] - (lease_lblt_tab[pre_idx] - lease_lblt_tab[cur_idx])
            # else:
            #     intr_exp = lease_fee_tab[cur_idx] - lease_lblt_tab[cur_idx]
            # intr_exp_tab.append(intr_exp)

            # 보증금 유효이자,현할차 계산 및 테이블 생성
            deposit_intr = round(deposit_npv * npv_rate)
            deposit_dscnt = deposit_dscnt - deposit_intr
            if cycle == self.period:
                deposit_intr = deposit_intr + deposit_dscnt
                deposit_dscnt = 0

            deposit_npv = deposit_npv + deposit_intr
            deposit_intr_tab.append(deposit_intr)
            deposit_dscnt_tab.append(deposit_dscnt)

            # 복구충당부채 전입액 계산 및 테이블 생성
            rstr_exp = round(rstr_alwn * npv_rate)
            rstr_alwn = rstr_alwn + rstr_exp
            if cycle == self.period:
                rstr_exp = rstr_exp + rstr_alwn_amt - rstr_alwn
                rstr_alwn = rstr_alwn_amt

            rstr_exp_tab.append(rstr_exp)
            rstr_alwn_tab.append(rstr_alwn)

        # # 리스료 테이블 역전, 정렬 맞추기 위한 0 추가
        # lease_fee_tab.remove(0)
        # lease_fee_tab.reverse()
        # lease_fee_tab.insert(0, 0)

        # 리스부채 테이블 역전, 정렬 맞추기 위한 0 추가
        lease_lblt_tab.reverse()
        lease_lblt_tab.append(0)

        # # 이자비용 테이블 역전, 정렬 맞추기 위한 0 삽입
        # intr_exp_tab.reverse()
        # intr_exp_tab.insert(0, 0)

        # 사용권자산 금액 계산
        lease_asset_tab[0] = lease_lblt_tab[0] + deposit_dscnt_tab[0] + rstr_alwn_tab[0] + prnt_asset

        for i in lease_cycle:
            # 감가상각비 및 감가상각누계액 테이블 생성
            if i < self.period:
                depr_exp = round(lease_asset_tab[i] / (self.period - i))
                lease_asset = lease_asset_tab[i] - depr_exp
                depr_exp_tab.append(depr_exp)
                lease_asset_tab.append(lease_asset)
                asset_diff = lease_asset_tab[i] - (lease_lblt_tab[i] + deposit_dscnt_tab[i] + rstr_alwn_tab[i])
                asset_diff_tab.append(asset_diff)

            # 이자비용 계산 및 테이블 생성
            if i > 0:
                intr_exp = lease_fee_tab[i] - (lease_lblt_tab[i-1] - lease_lblt_tab[i])
                # pre_idx = cycle - 1
                # cur_idx = cycle - 2
                # if cycle > 1:
                #     intr_exp = lease_fee_tab[pre_idx] - (lease_lblt_tab[pre_idx] - lease_lblt_tab[cur_idx])
                # else:
                #     intr_exp = lease_fee_tab[cur_idx] - lease_lblt_tab[cur_idx]
                intr_exp_tab.append(intr_exp)

        self.cycle = lease_cycle                #회차
        self.lease_fee = lease_fee_tab          #월 리스료
        self.lease_lbt = lease_lblt_tab         #리스부채
        self.lease_exp = intr_exp_tab           #이자비용
        self.deposit_dscnt = deposit_dscnt_tab  #보증금 현할차
        self.deposit_intr = deposit_intr_tab    #보증금이자
        self.rstr_exp = rstr_exp_tab            #복구충당부채 전입액
        self.rstr_alw = rstr_alwn_tab           #복구충당부채
        self.lease_dep = depr_exp_tab           #감가상각비
        self.lease_ast = lease_asset_tab        #사용권자산
        self.asset_diff_tab = asset_diff_tab

    def monthdelta(self, frdate, todate):
        # date1 = date.fromisoformat(frdate)
        # date2 = date.fromisoformat(todate)
        date1 = frdate
        date2 = todate
        monthdelta = (date2.year*12 + date2.month)-(date1.year*12 + date1.month) + 1
        return monthdelta
