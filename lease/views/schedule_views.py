from datetime import datetime, date
from flask import Blueprint, url_for, render_template, request, flash
from werkzeug.utils import redirect
from sqlalchemy.sql import func
from sqlalchemy import literal

from lease import db
from ..models import Contract, Baseline, Schedule, Leasecls
from ..forms import Report
from .auth_views import login_required
from ifrs16 import LeaseCalculate, date_fromto_compare

import sqlite3

bp = Blueprint('schedule', __name__, url_prefix='/schedule')


@bp.route('/schedule/<int:baseline_id>')
@login_required
def create(baseline_id):
    baseline = Baseline.query.get_or_404(baseline_id)
    contract = Contract.query.get_or_404(baseline.contract_id)

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
                            lease_dep=lease.lease_dep[i], dep_accum=lease.dep_accum[i], lease_ast=lease.lease_ast[i],
                            lease_acq=lease.lease_acq[i],
                            contract=contract, baseline=baseline, create_date=datetime.now())
        db.session.add(schedule)
    db.session.commit()
    return redirect(url_for('contract.detail', contract_id=baseline.contract_id))


@bp.route('/report/', methods=('GET', 'POST'))
def report():
    report = Report()
    if request.method == 'POST':
        report.frdate = request.values.get("frdate")
        report.todate = request.values.get("todate")

        if report.frdate != "" and report.todate != "":
            if report.frdate != report.todate:
                date_compare = date_fromto_compare(date.fromisoformat(report.frdate), date.fromisoformat(report.todate))
                if date_compare == False:
                    flash('조회기간 종료일은 시작일보다 커야 합니다.')
                    return render_template('contract/month_report.html',report=report)

        # 조회기간 비용수익 조회
        list_sql = db.session.query(Contract.leasecls_id, Leasecls.clsname,
                                    func.sum(Schedule.lease_fee).label("lease_fee"),
                                    func.sum(Schedule.lease_exp).label("lease_exp"),
                                    func.sum(Schedule.deposit_intr).label("deposit_intr"),
                                    func.sum(Schedule.lease_dep).label("lease_dep"),
                                    func.sum(Schedule.rstr_exp).label("rstr_exp")). \
            join(Baseline, Schedule.contract_id == Baseline.contract_id). \
            join(Contract, Schedule.contract_id == Contract.id). \
            outerjoin(Leasecls, Leasecls.id == Contract.leasecls_id). \
            filter(Schedule.exemonth.between(report.frdate, report.todate)). \
            group_by(Contract.leasecls_id)
        sum_sql = db.session.query(literal("0").label("leasecls_id"),literal("합계").label("clsname"),
                                   func.sum(Schedule.lease_fee).label("lease_fee"),
                                   func.sum(Schedule.lease_exp).label("lease_exp"),
                                   func.sum(Schedule.deposit_intr).label("deposit_intr"),
                                   func.sum(Schedule.lease_dep).label("lease_dep"),
                                   func.sum(Schedule.rstr_exp).label("rstr_exp")).\
            join(Baseline, Schedule.contract_id == Baseline.contract_id).\
            join(Contract, Schedule.contract_id == Contract.id).\
            filter(Schedule.exemonth.between(report.frdate,report.todate))
        prdpl = list_sql.union_all(sum_sql).all()


        # 잔액조회
        list_sql = db.session.query(Contract.leasecls_id,Leasecls.clsname,
                                    func.sum(Schedule.lease_lbt).label("lease_lbt"),
                                    func.sum(Schedule.deposit_dscnt).label("deposit_dscnt"),
                                    func.sum(Schedule.rstr_alw).label("rstr_alw"),
                                    func.sum(Schedule.lease_acq).label("lease_acq"),
                                    func.sum(Schedule.dep_accum).label("dep_accum")).\
            join(Baseline, Schedule.contract_id == Baseline.contract_id).\
            join(Contract, Schedule.contract_id == Contract.id).\
            outerjoin(Leasecls, Leasecls.id == Contract.leasecls_id).\
            filter(Schedule.exemonth == report.todate).\
            group_by(Contract.leasecls_id)
        sum_sql = db.session.query(literal("0").label("leasecls_id"),literal("합계").label("clsname"),
                                   func.sum(Schedule.lease_lbt).label("lease_lbt"),
                                   func.sum(Schedule.deposit_dscnt).label("deposit_dscnt"),
                                   func.sum(Schedule.rstr_alw).label("rstr_alw"),
                                   func.sum(Schedule.lease_acq).label("lease_acq"),
                                   func.sum(Schedule.dep_accum).label("dep_accum")).\
            join(Baseline, Schedule.contract_id == Baseline.contract_id).\
            join(Contract, Schedule.contract_id == Contract.id).\
            filter(Schedule.exemonth == report.todate)
        balance = list_sql.union_all(sum_sql).all()

        conn = sqlite3.connect("lease.db")
        cur = conn.cursor()

        # 마이그레이션 후, 계산 집계
        cur.execute(
            "SELECT sum(lease_lbt), sum(deposit_dscnt), sum(rstr_alw), sum(lease_acq), sum(dep_accum) "
            "FROM schedule WHERE cycle = '0' AND exemonth = '2021-04-01';")
        result = cur.fetchone()
        report.mig_lease_lbt = result[0]
        report.mig_deposit_dscnt = result[1]
        report.mig_rstr_alw = result[2]
        report.mig_lease_ast = result[3]
        report.mig_dep_accum = result[4]

        # 마이그레이션 값 집계
        cur.execute(
            "SELECT sum(prnt_lblti),sum(prnt_dpsit),sum(prnt_rstra),(sum(prnt_asset)+sum(prnt_depac)) as sumv,sum(prnt_depac) "
            "FROM baseline WHERE startdate = '2021-04-01';")
        result = cur.fetchone()
        report.prnt_lblti = result[0]
        report.prnt_dpsit = result[1]
        report.prnt_rstra = result[2]
        report.prnt_asset = result[3]
        report.prnt_depac = result[4]

        conn.close()

        return render_template('contract/report_sum.html',report=report, balance=balance, prdpl=prdpl)

    return render_template('contract/report_sum.html',report=report)


@bp.route('/prdreport/', methods=('GET', 'POST'))
def prdreport():
    report = Report()
    if request.method == 'POST':
        report.todate = request.values.get("todate")

        # 잔액조회
        list_sql = db.session.query(Contract.leasecls_id,Leasecls.clsname,Contract.id,Contract.subject,
                                    Schedule.lease_fee,Schedule.lease_exp,Schedule.lease_lbt,
                                    Schedule.deposit_dscnt,Schedule.deposit_intr,
                                    Schedule.rstr_exp, Schedule.rstr_alw,
                                    Schedule.lease_dep, Schedule.lease_acq, Schedule.dep_accum).\
            join(Baseline, Schedule.contract_id == Baseline.contract_id).\
            join(Contract, Schedule.contract_id == Contract.id).\
            outerjoin(Leasecls, Leasecls.id == Contract.leasecls_id).\
            filter(Schedule.exemonth == report.todate,
                   Baseline.startdate < report.todate, Baseline.enddate >= report.todate)
        sum_sql = db.session.query(literal("0").label("leasecls_id"),literal("합계").label("clsname"),
                                   literal("0").label("id"),literal("합계").label("subject"),
                                   func.sum(Schedule.lease_fee).label("lease_fee"),
                                   func.sum(Schedule.lease_exp).label("lease_exp"),
                                   func.sum(Schedule.lease_lbt).label("lease_lbt"),
                                   func.sum(Schedule.deposit_dscnt).label("deposit_dscnt"),
                                   func.sum(Schedule.deposit_intr).label("deposit_intr"),
                                   func.sum(Schedule.rstr_exp).label("rstr_exp"),
                                   func.sum(Schedule.rstr_alw).label("rstr_alw"),
                                   func.sum(Schedule.lease_dep).label("lease_dep"),
                                   func.sum(Schedule.lease_acq).label("lease_acq"),
                                   func.sum(Schedule.dep_accum).label("dep_accum")).\
            join(Baseline, Schedule.contract_id == Baseline.contract_id).\
            join(Contract, Schedule.contract_id == Contract.id).\
            filter(Schedule.exemonth == report.todate)
        balance = sum_sql.union_all(list_sql).all()

        return render_template('contract/report_items.html',report=report, balance=balance)

    return render_template('contract/report_items.html',report=report)


@bp.route('/report2/', methods=('GET', 'POST'))
def report2():
    report = Report()
    if request.method == 'POST':
        report.frdate = request.values.get("frdate")
        report.todate = request.values.get("todate")

        if report.frdate != "" and report.todate != "":
            if report.frdate != report.todate:
                date_compare = date_fromto_compare(date.fromisoformat(report.frdate), date.fromisoformat(report.todate))
                if date_compare == False:
                    flash('조회기간 종료일은 시작일보다 커야 합니다.')
                    return render_template('contract/month_report.html',report=report)

        conn = sqlite3.connect("lease.db")
        cur = conn.cursor()

        param_range = []
        param_range.append(str(report.frdate))
        param_range.append(str(report.todate))

        param = []
        param.append(str(report.todate))


        # param = ['2021-04-01', '2021-06-30']

        # 월 상각비 집계
        cur.execute(
            "SELECT sum(lease_exp),sum(deposit_intr),sum(lease_dep) "
            "FROM schedule WHERE exemonth BETWEEN ? AND ?;",param_range)
        result = cur.fetchone()
        report.lease_exp = result[0]
        report.deposit_intr = result[1]
        report.lease_dep = result[2]

        # 월 시점 잔액
        cur.execute(
            "SELECT sum(lease_lbt), sum(deposit_dscnt), sum(rstr_alw), sum(lease_acq), sum(dep_accum) "
            "FROM schedule WHERE exemonth = ?;",param)
        result = cur.fetchone()
        report.lease_lbt = result[0]
        report.deposit_dscnt = result[1]
        report.rstr_alw = result[2]
        report.lease_ast = result[3]
        report.dep_accum = result[4]

        # 마이그레이션 후, 계산 집계
        cur.execute(
            "SELECT sum(lease_lbt), sum(deposit_dscnt), sum(rstr_alw), sum(lease_acq), sum(dep_accum) "
            "FROM schedule WHERE cycle = '0' AND exemonth BETWEEN ? AND ?;",param_range)
        result = cur.fetchone()
        report.mig_lease_lbt = result[0]
        report.mig_deposit_dscnt = result[1]
        report.mig_rstr_alw = result[2]
        report.mig_lease_ast = result[3]
        report.mig_dep_accum = result[4]

        # 마이그레이션 값 집계
        cur.execute(
            "SELECT sum(prnt_lblti),sum(prnt_dpsit),sum(prnt_rstra),(sum(prnt_asset)+sum(prnt_depac)) as sumv,sum(prnt_depac) "
            "FROM baseline WHERE startdate BETWEEN ? AND ?;",param_range)
        result = cur.fetchone()
        report.prnt_lblti = result[0]
        report.prnt_dpsit = result[1]
        report.prnt_rstra = result[2]
        report.prnt_asset = result[3]
        report.prnt_depac = result[4]

        conn.close()

        return render_template('contract/month_report.html',report=report)

    return render_template('contract/month_report.html',report=report)