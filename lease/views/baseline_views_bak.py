from datetime import datetime
from flask import Blueprint, url_for, render_template, request, flash, g
from werkzeug.utils import redirect

from lease import db
from ..models import Contract, Baseline, Schedule
from ..forms import BaselineForm
from .auth_views import login_required

from ifrs16 import LeaseCalculate, date_fromto_compare, last_day_of_month, previous_month

bp = Blueprint('baseline', __name__, url_prefix='/baseline')


@bp.route('/detail/<int:baseline_id>/')
def detail(baseline_id):
    baseline = Baseline.query.get_or_404(baseline_id)
    contract = Contract.query.get_or_404(baseline.contract_id)
    return render_template('contract/baseline_detail.html', baseline=baseline, basenode_id=contract.basenode_id)


@bp.route('/create/<int:contract_id>', methods=('GET', 'POST'))
@login_required
def create(contract_id):
    global baseline, basenode, prnt_asset, prnt_depac, prnt_lblti, prnt_dpsit, prnt_rstra
    contract = Contract.query.get_or_404(contract_id)
    for baseline in contract.baseline_set:
        baseline = baseline
        basenode = baseline.id

    if len(contract.schedule_set) > 0:
        form = BaselineForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                date_compare = date_fromto_compare(form.startdate.data, form.changedate.data)
                if date_compare == False:
                    flash('수정계약일이 종전시작일 이전일 수 없습니다.')
                    return render_template('contract/baseline_form.html', form=form)

                date_compare = date_fromto_compare(form.changedate.data, form.enddate.data)
                if date_compare == False:
                    flash('종료일은 수정계약일보다 커야 합니다.')
                    return render_template('contract/baseline_form.html', form=form)

                basedate = form.changedate.data

                # 기존 스케줄에 연결된 계약번호 지우기
                for schedule in contract.schedule_set:
                    if schedule.exemonth > basedate:
                        schedule.contract_id = None
                    else:
                        prnt_asset = schedule.lease_ast
                        prnt_depac = schedule.dep_accum
                        prnt_lblti = schedule.lease_lbt
                        prnt_dpsit = schedule.deposit_dscnt
                        prnt_rstra = schedule.rstr_alw
                db.session.commit()

                baseline = Baseline(contract=contract, startdate=form.changedate.data, enddate=form.enddate.data,
                                    rate=form.rate.data, lease_fee=form.lease_fee.data, init_fee=form.lease_fee.data,
                                    deposit=form.deposit.data, rstr_alwn=form.rstr_alwn.data,
                                    prnt_asset=prnt_asset, prnt_depac=prnt_depac, prnt_lblti=prnt_lblti,
                                    prnt_dpsit=prnt_dpsit, prnt_rstra=prnt_rstra,
                                    basenode_id=basenode, create_date=datetime.now(), user=g.user)
                db.session.add(baseline)
                contract.basenode_id = basenode
                db.session.commit()

                return redirect(url_for('schedule.create', baseline_id=baseline.id))

        else:
            form = BaselineForm(obj=baseline)

    else:
        return redirect(url_for('schedule.create', baseline_id=baseline.id))

    return render_template('contract/baseline_form.html', form=form)


@bp.route('/recreate/<int:contract_id>', methods=('GET', 'POST'))
@login_required
def recreate(contract_id):
    global baseline, basenode
    contract = Contract.query.get_or_404(contract_id)
    for baseline in contract.baseline_set:
        baseline = baseline
        basenode = baseline.id

    form = BaselineForm()
    if request.method == 'POST':
        # form = BaselineForm()
        if form.validate_on_submit():
            date_compare = date_fromto_compare(form.startdate.data, form.changedate.data)
            if date_compare == False:
                flash('수정계약일이 종전시작일 이전일 수 없습니다.')
                return render_template('contract/baseline_form.html', form=form)

            date_compare = date_fromto_compare(form.changedate.data, form.enddate.data)
            if date_compare == False:
                flash('종료일은 수정계약일보다 커야 합니다.')
                return render_template('contract/baseline_form.html', form=form)

            basedate = form.changedate.data
            prnt_asset = 0
            prnt_depac = 0

            # 기존 스케줄에 연결된 계약번호 지우기
            for schedule in contract.schedule_set:
                if schedule.exemonth < basedate:
                    prnt_asset = schedule.lease_ast
                    prnt_depac = schedule.dep_accum
                    # prnt_lease = schedule.lease_ast - (schedule.lease_lbt + schedule.deposit_dscnt + schedule.rstr_alw)
                    prnt_lease = schedule.lease_lbt + schedule.deposit_dscnt + schedule.rstr_alw
                else:
                    schedule.contract_id = None
            db.session.commit()

            baseline = Baseline(contract=contract, startdate=form.changedate.data, enddate=form.enddate.data,
                                rate=form.rate.data, lease_fee=form.lease_fee.data, deposit=form.deposit.data,
                                rstr_alwn=form.rstr_alwn.data, prnt_asset=prnt_lease, basenode_id = basenode,
                                create_date=datetime.now(), user=g.user)
            db.session.add(baseline)
            contract.basenode_id = basenode

            frate = float(baseline.rate)
            lease = LeaseCalculate(baseline.startdate, baseline.enddate, frate, baseline.lease_fee, 0, baseline.deposit, baseline.rstr_alwn, prnt_asset, prnt_depac, prnt_lease)
            for i in lease.cycle:
                schedule = Schedule(cycle=lease.cycle[i], exemonth=lease.exemonth[i], lease_fee=lease.lease_fee[i],
                                    lease_lbt=lease.lease_lbt[i], lease_exp=lease.lease_exp[i],
                                    deposit_dscnt=lease.deposit_dscnt[i], deposit_intr=lease.deposit_intr[i],
                                    rstr_exp=lease.rstr_exp[i], rstr_alw=lease.rstr_alw[i],
                                    lease_dep=lease.lease_dep[i], dep_accum=lease.dep_accum[i], lease_ast=lease.lease_ast[i],
                                    contract=contract, baseline=baseline, create_date=datetime.now())
                db.session.add(schedule)
            db.session.commit()
            return redirect(url_for('contract.detail', contract_id=contract_id))
    else:
        form = BaselineForm(obj=baseline)

    return render_template('contract/baseline_form.html', form=form)


@bp.route('/delete1/<int:contract_id>')
def delete1(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    for schedule in contract.schedule_set:
        db.session.delete(schedule)
    # for baseline in contract.baseline_set:
    #     for schedule in baseline.schedule_set:
    #         db.session.delete(schedule)
    #     db.session.delete(baseline)
    db.session.commit()
    return redirect(url_for('contract.detail', contract_id=contract_id))


@bp.route('/delete/<int:baseline_id>')
def delete(baseline_id):
    global basedate
    baseline = Baseline.query.get_or_404(baseline_id)
    contract = Contract.query.get_or_404(baseline.contract_id)
    if baseline.basenode_id != contract.basenode_id:
        flash('마지막 수정 계약만 삭제할 수 있습니다.')
        return redirect(url_for('baseline.detail', baseline_id=baseline_id))

    basenode = Baseline.query.get_or_404(baseline.basenode_id)
    for schedule in baseline.schedule_set:
        if schedule.cycle == 0:
            basedate = schedule.exemonth
        db.session.delete(schedule)
    db.session.delete(baseline)

    # 기존 스케줄에 연결된 계약번호 재연결
    for schedule in basenode.schedule_set:
        if schedule.exemonth > basedate:
            schedule.contract_id = basenode.contract_id

    contract.basenode_id = basenode.basenode_id
    db.session.commit()

    return redirect(url_for('contract.detail', contract_id=contract.id))
