from lease.models import Contract, Baseline, Schedule, Leasecls, User
from datetime import date, datetime
from lease import db
from ifrs16 import LeaseCalculate

class Mass:
    def __init__(self,leasecls_id,subject,startdate,enddate,rate,lease_fee,init_fee,deposit,rstr_alwn,
                 prnt_asset,prnt_depac,prnt_lblti,prnt_dpsit,prnt_rstra):
        dbobj = self.create(leasecls_id,subject,startdate,enddate,rate,lease_fee,init_fee,deposit,rstr_alwn,
                            prnt_asset,prnt_depac,prnt_lblti,prnt_dpsit,prnt_rstra)

    def create(self, leasecls_id, subject, startdate, enddate, rate, lease_fee, init_fee, deposit, rstr_alwn,
                 prnt_asset, prnt_depac, prnt_lblti, prnt_dpsit, prnt_rstra):

        user = User.query.filter_by(id='1').first()
        leasecls = Leasecls.query.filter_by(id=leasecls_id).first()
        contract = Contract(subject=subject,
                            startdate=date.fromisoformat(startdate),
                            enddate=date.fromisoformat(enddate),
                            rate=rate, lease_fee=lease_fee, init_fee=init_fee,
                            deposit=deposit, rstr_alwn=rstr_alwn, create_date=datetime.now(),
                            leasecls=leasecls, user=user)
        baseline = Baseline(contract=contract, startdate=contract.startdate, enddate=contract.enddate,
                        rate=contract.rate, lease_fee=contract.lease_fee, init_fee=contract.init_fee,
                        deposit=contract.deposit, rstr_alwn=contract.rstr_alwn, prnt_asset=prnt_asset,
                        prnt_depac=prnt_depac, prnt_lblti=prnt_lblti,
                        prnt_dpsit=prnt_dpsit, prnt_rstra=prnt_rstra,
                        create_date=contract.create_date, user=user)
        self.user = user
        self.contract = contract
        self.baseline = baseline
        db.session.add(contract)
        db.session.add(baseline)

        # 리스 상각스케줄 계산
        frate = float(baseline.rate)
        lease = LeaseCalculate(baseline.startdate, baseline.enddate, frate, baseline.lease_fee, baseline.init_fee,
                               baseline.deposit, baseline.rstr_alwn, baseline.prnt_asset,
                               baseline.prnt_depac, baseline.prnt_lblti, baseline.prnt_dpsit, baseline.prnt_rstra)

        # 상각스케줄 저장
        for i in lease.cycle:
            schedule = Schedule(cycle=lease.cycle[i], exemonth=lease.exemonth[i], lease_fee=lease.lease_fee[i],
                                lease_lbt=lease.lease_lbt[i], lease_exp=lease.lease_exp[i],
                                deposit_dscnt=lease.deposit_dscnt[i], deposit_intr=lease.deposit_intr[i],
                                rstr_exp=lease.rstr_exp[i], rstr_alw=lease.rstr_alw[i],
                                lease_dep=lease.lease_dep[i], dep_accum=lease.dep_accum[i],
                                lease_ast=lease.lease_ast[i], lease_acq=lease.lease_acq[i],
                                contract=contract, baseline=baseline, create_date=datetime.now())
            db.session.add(schedule)

    def confirm(self):
        db.session.commit()
