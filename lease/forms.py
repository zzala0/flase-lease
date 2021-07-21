from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, IntegerField, FloatField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length, EqualTo, Email


class ContractForm(FlaskForm):
    subject = StringField('계약명', validators=[DataRequired()])
    startdate = DateField('계약시작일', format='%Y-%m-%d', validators=[DataRequired()])
    enddate = DateField('계약종료일', format='%Y-%m-%d', validators=[DataRequired()])
    rate = FloatField('할인율', validators=[DataRequired()])
    # lease_fee = IntegerField('고정리스료', validators=[DataRequired()])
    lease_fee = IntegerField('고정리스료')
    init_fee = IntegerField('최초리스료')
    deposit = IntegerField('보증금')
    rstr_alwn = IntegerField('복구충당부채')
    leasecls_id = IntegerField('리스구분')

    prnt_asset = IntegerField('이전 사용권자산')
    prnt_depac = IntegerField('이전 상각누계액')
    prnt_lblti = IntegerField('이전 리스부채')
    prnt_dpsit = IntegerField('이전 보증금')
    prnt_rstra = IntegerField('이전 복구충당부채')


class BaselineForm(FlaskForm):
    startdate = DateField('계약시작일', format='%Y-%m-%d')
    changedate = DateField('수정계약일', format='%Y-%m-%d', validators=[DataRequired()])
    enddate = DateField('계약종료일', format='%Y-%m-%d')
    rate = FloatField('할인율')
    lease_fee = IntegerField('고정리스료')
    init_fee = IntegerField('최초리스료')
    deposit = IntegerField('보증금')
    rstr_alwn = IntegerField('복구충당부채')


class UserCreateForm(FlaskForm):
    username = StringField('사용자이름', validators=[DataRequired(), Length(min=3, max=25)])
    password1 = PasswordField('비밀번호', validators=[
        DataRequired(), EqualTo('password2', '비밀번호가 일치하지 않습니다')])
    password2 = PasswordField('비밀번호확인', validators=[DataRequired()])
    email = EmailField('이메일', validators=[DataRequired(), Email()])

class UserLoginForm(FlaskForm):
    username = StringField('사용자이름', validators=[DataRequired(), Length(min=3, max=25)])
    password = PasswordField('비밀번호', validators=[DataRequired()])

class Report:
    def __init__(self):
        self.frdate = ""
        self.todate = ""
        self.lease_exp = 0
        self.deposit_intr = 0
        self.lease_dep = 0

        self.lease_lbt = 0
        self.deposit_dscnt = 0
        self.rstr_alw = 0
        self.lease_ast = 0
        self.dep_accum = 0

        self.mig_lease_lbt = 0
        self.mig_deposit_dscnt = 0
        self.mig_rstr_alw = 0
        self.mig_lease_ast = 0
        self.mig_dep_accum = 0

        self.prnt_lblti = 0
        self.prnt_dpsit = 0
        self.prnt_rstra = 0
        self.prnt_asset = 0
        self.prnt_depac = 0

        self.msgtype = ""