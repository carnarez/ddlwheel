"""."""


def test_fetch_children():
    """."""
    q = """create or replace procedure random_schema.run_it() language plpgsql as $$

    begin

    drop table if exists random_other_schema.the_table

    select
      cast(column1 as integer),
      column2,
      column3
    into random_other_schema.the_table.the_table
    from random_other_schema.another_table src1
    join (
      select *
      from random_other_schema.yet_another_table
    ) src2
    on src1.colunm1 = src2.column1

    return

    end

    $$
    """
