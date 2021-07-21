import numpy_financial as npf
import datetime
from dateutil.relativedelta import relativedelta

class LeaseCalculate:
    def __init__(self, frdate, todate, rate, lease_fee, lease_init_fee=0, deposit_amt=0, rstr_alwn_amt=0,
                 prnt_asset=0, prnt_depac=0, prnt_lblti=0, prnt_dpsit=0, prnt_rstra=0):

        self.period = self.monthdelta(frdate, todate)

        # 리스 사이클
        lease_cycle = [0]
        # 리스료 테이블
        lease_fee_tab = [0]
        # 리스지급월 테이블
        lease_mon_tab = [frdate]
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
        # 감가상각누계 테이블
        # depr_accum_tab = [0]
        depr_accum_tab = [prnt_depac]
        # 사용권자산 테이블
        lease_asset_tab = [0]
        lease_assetacq_tab = [0]
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
            # NPV를 마지막 지급분부터 쌓아나가나, 마지막 계산시에는 최초에 포함되어야 하므로,
            # 최초 지급금액을 마지막 회차시 첫번째 항목에 삽입한다.
            if cycle == self.period:
                if lease_init_fee == 0:
                    lease_fee_tab.append(lease_fee)
                else:
                    lease_fee_tab.insert(1, lease_init_fee)
            else:
                lease_fee_tab.append(lease_fee)

            # 리스지급월 테이블 생성
            if cycle == 1:
                exemonth = last_day_of_month(frdate)
            else:
                exemonth = self.next_month(lease_mon_tab[cycle-1])
                exemonth = last_day_of_month(exemonth)
            lease_mon_tab.append(exemonth)

            # 리스부채 NPV 계산
            # 엑셀NPV는 인자가 1개부터 시작하나, NUMPY에선 시작값이 2개부터라 엑셀과 같은 결과를 얻기 위해선 리스트앞에 빈값이 있어야 한다.
            lease_lblt = round(npf.npv(npv_rate, lease_fee_tab))
            # 리스부채총액 계산 및 테이블 생성
            lease_lblt_tab.append(lease_lblt)

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

        # 리스부채 테이블 역전, 정렬 맞추기 위한 0 추가
        lease_lblt_tab.reverse()
        lease_lblt_tab.append(0)

        # 사용권자산 금액 계산
        depr_accum = prnt_depac
        # lease_asset_tab[0] = lease_lblt_tab[0] + deposit_dscnt_tab[0] + rstr_alwn_tab[0] + \
        #                      prnt_asset + prnt_depac - (prnt_lblti + prnt_dpsit + prnt_rstra)
        lease_asset_tab[0] = lease_lblt_tab[0] + deposit_dscnt_tab[0] + rstr_alwn_tab[0] + \
                             prnt_asset - (prnt_lblti + prnt_dpsit + prnt_rstra)
        lease_assetacq_tab[0] = lease_asset_tab[0] + prnt_depac

        for i in lease_cycle:
            # 감가상각비 및 감가상각누계액 테이블 생성
            if i < self.period:
                depr_exp = round(lease_asset_tab[i] / (self.period - i))
                # depr_exp = round((lease_asset_tab[0]-depr_accum_tab[i]) / (self.period - i))
                depr_accum = depr_accum + depr_exp
                lease_asset = lease_asset_tab[i] - depr_exp
                # if i == 0:
                #     lease_asset = lease_asset_tab[i] - depr_accum
                # else:
                #     lease_asset = lease_asset_tab[i] - depr_exp
                depr_exp_tab.append(depr_exp)
                depr_accum_tab.append(depr_accum)
                lease_asset_tab.append(lease_asset)
                lease_assetacq_tab.append(lease_assetacq_tab[0])
                asset_diff = lease_asset_tab[i] - (lease_lblt_tab[i] + deposit_dscnt_tab[i] + rstr_alwn_tab[i])
                asset_diff_tab.append(asset_diff)

            # 이자비용 계산 및 테이블 생성
            if i > 0:
                intr_exp = lease_fee_tab[i] - (lease_lblt_tab[i-1] - lease_lblt_tab[i])
                intr_exp_tab.append(intr_exp)

        self.cycle = lease_cycle                #회차
        self.lease_fee = lease_fee_tab          #월 리스료
        self.exemonth = lease_mon_tab           #실행월
        self.lease_lbt = lease_lblt_tab         #리스부채
        self.lease_exp = intr_exp_tab           #이자비용
        self.deposit_dscnt = deposit_dscnt_tab  #보증금 현할차
        self.deposit_intr = deposit_intr_tab    #보증금이자
        self.rstr_exp = rstr_exp_tab            #복구충당부채 전입액
        self.rstr_alw = rstr_alwn_tab           #복구충당부채
        self.lease_dep = depr_exp_tab           #감가상각비
        self.dep_accum = depr_accum_tab         #감가상각누계
        self.lease_ast = lease_asset_tab        #사용권자산잔액
        self.lease_acq = lease_assetacq_tab     #사용권자산
        self.asset_diff = asset_diff_tab

    def monthdelta(self, frdate, todate):
        # date1 = date.fromisoformat(frdate)
        # date2 = date.fromisoformat(todate)
        date1 = frdate
        date2 = todate
        monthdelta = (date2.year*12 + date2.month)-(date1.year*12 + date1.month) + 1
        return monthdelta

    def next_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        next_month.replace(day=1)
        # next_month = next_month.date()
        return next_month

def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    last_day = next_month - datetime.timedelta(days=next_month.day)
    # last_day = last_day.date()
    return last_day

def previous_month(any_day):
    prev_day = any_day.replace(day=1) - datetime.timedelta(days=1)
    return prev_day

def date_fromto_compare(date1, date2):
    from datetime import date
    result = True
    frdate = date.isoformat(date1)
    todate = date.isoformat(date2)
    if frdate >= todate:
        result = False
    return result