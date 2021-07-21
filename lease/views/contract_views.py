from datetime import datetime
from flask import Blueprint, render_template, url_for, request, flash, g
from werkzeug.utils import redirect

from lease import db
from ..models import Contract, Baseline, Leasecls, User
from ..forms import ContractForm
from .auth_views import login_required
from ifrs16 import date_fromto_compare

bp = Blueprint('contract', __name__, url_prefix='/contract')


@bp.route('/list/')
def _list():
    # 입력 파라미터
    page = request.args.get('page', type=int, default=1)
    kw = request.args.get('kw', type=str, default='')

    # 조회
    contract_list = Contract.query.order_by(Contract.create_date.desc())
    if kw:
        search = '%%{}%%'.format(kw)
        contract_list = contract_list \
            .outerjoin(User) \
            .outerjoin(Baseline).filter(
            Contract.subject.ilike(search) |
            Contract.lease_fee.ilike(search) |
            User.username.ilike(search)
        ).distinct()

    # 페이징
    contract_list = contract_list.paginate(page, per_page=20)
    return render_template('contract/contract_list.html', contract_list=contract_list, page=page, kw=kw)


@bp.route('/detail/<int:contract_id>/')
def detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    cycle = []
    for idx, schedule in enumerate(contract.schedule_set):
        cycle.append(idx)
    return render_template('contract/contract_detail.html', contract=contract, cycle=cycle)


@bp.route('/create/', methods=('GET', 'POST'))
@login_required
def create():
    leasecls_list = Leasecls.query.all()
    form = ContractForm()
    if request.method == 'POST':
        if form.startdate.data != None and form.enddate.data != None:
            date_compare = date_fromto_compare(form.startdate.data, form.enddate.data)
            if date_compare == False:
                flash('종료일은 시작일보다 커야 합니다.')
                return render_template('contract/contract_form.html', form=form, leasecls_list=leasecls_list)

        if form.validate_on_submit():
            leasecls = Leasecls.query.get_or_404(form.leasecls_id.data)
            contract = Contract(subject=form.subject.data, startdate=form.startdate.data, enddate=form.enddate.data,
                                rate=form.rate.data, lease_fee=form.lease_fee.data, init_fee=form.init_fee.data,
                                deposit=form.deposit.data, rstr_alwn=form.rstr_alwn.data, create_date=datetime.now(),
                                user=g.user, leasecls=leasecls)
            db.session.add(contract)

            baseline = Baseline(contract=contract, startdate=contract.startdate, enddate=contract.enddate,
                                rate=contract.rate, lease_fee=contract.lease_fee, init_fee=contract.init_fee,
                                deposit=contract.deposit, rstr_alwn=contract.rstr_alwn, prnt_asset=form.prnt_asset.data,
                                prnt_depac=form.prnt_depac.data, prnt_lblti=form.prnt_lblti.data,
                                prnt_dpsit=form.prnt_dpsit.data, prnt_rstra=form.prnt_rstra.data,
                                create_date=datetime.now(), user=g.user)
            db.session.add(baseline)

            db.session.commit()
            return redirect(url_for('contract._list'))
            # flash('저장이 왜 안되지?')
            # return render_template('contract/contract_form.html', form=form, leasecls_list=leasecls_list)
    return render_template('contract/contract_form.html', form=form, leasecls_list=leasecls_list)


@bp.route('/modify/<int:contract_id>', methods=('GET', 'POST'))
@login_required
def modify(contract_id):
    global baseline
    leasecls_list = Leasecls.query.all()
    contract = Contract.query.get_or_404(contract_id)
    for baseline in contract.baseline_set:
        baseline = baseline

    # if g.user != contract.user:
    #     flash('수정권한이 없습니다')
    #     return redirect(url_for('contract.detail', contract_id=contract_id))

    if request.method == 'POST':
        form = ContractForm()
        if form.validate_on_submit():
            form.populate_obj(contract)
            contract.modify_date = datetime.now()  # 수정일시 저장

            for baseline in contract.baseline_set:
                form.populate_obj(baseline)

            db.session.commit()
            return redirect(url_for('contract.detail', contract_id=contract_id))
    else:
        form = ContractForm(obj=contract)
        form.prnt_asset.data = baseline.prnt_asset
        form.prnt_depac.data = baseline.prnt_depac
        form.prnt_lblti.data = baseline.prnt_lblti
        form.prnt_dpsit.data = baseline.prnt_dpsit
        form.prnt_rstra.data = baseline.prnt_rstra
    return render_template('contract/contract_form.html', form=form, leasecls_list=leasecls_list)


@bp.route('/delete/<int:contract_id>')
@login_required
def delete(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    if g.user != contract.user:
        flash('삭제권한이 없습니다')
        return redirect(url_for('contract.detail', contract_id=contract_id))

    for baseline in contract.baseline_set:
        for schedule in baseline.schedule_set:
            db.session.delete(schedule)
        db.session.delete(baseline)
    db.session.delete(contract)
    db.session.commit()
    return redirect(url_for('contract._list'))
