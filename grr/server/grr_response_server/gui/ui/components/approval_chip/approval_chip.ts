import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {DateTime} from '../../lib/date_time';
import {ApprovalStatus, type Approval} from '../../lib/models/user';

const TITLES: {readonly [key in ApprovalStatus['type']]: string} = {
  'expired': 'No access',
  'invalid': 'No access',
  'pending': 'Access pending',
  'valid': 'Access granted',
};

/** Chip that shows the validity of an Approval. */
@Component({
  standalone: false,
  selector: 'app-approval-chip',
  templateUrl: './approval_chip.ng.html',
  styleUrls: ['./approval_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalChip {
  @Input()
  set approval(approval: Approval | null) {
    this.approval$.next(approval);
  }

  get approval() {
    return this.approval$.getValue();
  }

  get timeUntilExpiry() {
    if (this.approval && this.approval.expirationTime) {
      const date = DateTime.fromJSDate(this.approval.expirationTime);
      return ` –  ${date.toRelative()!.replace('in ', '')} left`;
    } else {
      return '';
    }
  }

  private readonly approval$ = new BehaviorSubject<Approval | null>(null);
  readonly status$ = this.approval$.pipe(
    map((approval) => approval?.status.type ?? 'invalid'),
  );

  readonly title$ = this.status$.pipe(map((status) => TITLES[status]));
}
