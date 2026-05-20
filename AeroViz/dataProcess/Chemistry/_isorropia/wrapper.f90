! wrapper.f90
! Modern Fortran wrapper around the F77 ISORROPIAII_MAIN_MOD module.
! Exposes two entry points designed for f2py to wrap cleanly with
! explicit intent(in)/intent(out) and float64 (real*8) bindings:
!
!   solve()       — single sample
!   solve_batch() — vectorised over many samples (one ISORROPIA call per row)
!
! Verified to produce results identical to the bundled isrpia2.exe (to
! within machine precision) for a range of sulfate/ammonia/nitrate
! conditions on macOS arm64. See ISORROPIA copyright notice in
! isorropiaII_main_mod.F and THIRD_PARTY_NOTICES.md.

module isorropia_wrap
   use isorropiaii_main_mod, only: ISORROPIA
   implicit none
   private
   public :: solve, solve_batch

contains

   ! --- Single sample ----------------------------------------------------
   subroutine solve(wi, rhi, tempi, cntrl, &
                    wt, gas, aerliq, aersld, other, scasi)
      real*8, intent(in)  :: wi(8)
      real*8, intent(in)  :: rhi
      real*8, intent(in)  :: tempi
      real*8, intent(in)  :: cntrl(2)
      real*8, intent(out) :: wt(8)
      real*8, intent(out) :: gas(3)
      real*8, intent(out) :: aerliq(15)
      real*8, intent(out) :: aersld(19)
      real*8, intent(out) :: other(9)
      character(len=15), intent(out) :: scasi

      call ISORROPIA(wi, rhi, tempi, cntrl, &
                     wt, gas, aerliq, aersld, scasi, other)
   end subroutine solve

   ! --- Batch (one call per row, no Python loop overhead) ----------------
   subroutine solve_batch(n, wi_arr, rhi_arr, tempi_arr, cntrl, &
                          wt_arr, gas_arr, aerliq_arr, aersld_arr, other_arr)
      integer, intent(in) :: n
      real*8, intent(in)  :: wi_arr(8, n)
      real*8, intent(in)  :: rhi_arr(n)
      real*8, intent(in)  :: tempi_arr(n)
      real*8, intent(in)  :: cntrl(2)
      real*8, intent(out) :: wt_arr(8, n)
      real*8, intent(out) :: gas_arr(3, n)
      real*8, intent(out) :: aerliq_arr(15, n)
      real*8, intent(out) :: aersld_arr(19, n)
      real*8, intent(out) :: other_arr(9, n)

      integer :: i
      character(len=15) :: scasi_tmp

      do i = 1, n
         call ISORROPIA(wi_arr(:, i), rhi_arr(i), tempi_arr(i), cntrl, &
                        wt_arr(:, i), gas_arr(:, i), aerliq_arr(:, i), &
                        aersld_arr(:, i), scasi_tmp, other_arr(:, i))
      end do
   end subroutine solve_batch

end module isorropia_wrap
