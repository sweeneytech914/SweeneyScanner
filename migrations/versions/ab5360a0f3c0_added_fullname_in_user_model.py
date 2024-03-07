"""added fullname in user model

Revision ID: ab5360a0f3c0
Revises: 9eceea5b60e4
Create Date: 2024-03-08 02:21:48.950481

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab5360a0f3c0'
down_revision = '9eceea5b60e4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fullname', sa.String(length=120), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('fullname')

    # ### end Alembic commands ###
