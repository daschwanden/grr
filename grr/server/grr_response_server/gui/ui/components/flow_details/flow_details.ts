import {Clipboard} from '@angular/cdk/clipboard';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ComponentRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  ViewChild,
  ViewContainerRef,
} from '@angular/core';
import {BehaviorSubject, Observable, combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';
import {makeFlowLink} from '../../lib/routing';

import {
  ButtonType,
  ExportMenuItem,
  Plugin as FlowDetailsPlugin,
} from '../../components/flow_details/plugins/plugin';
import {
  FlowState,
  FlowType,
  getFlowTitleFromFlow,
  type Flow,
  type FlowDescriptor,
} from '../../lib/models/flow';
import {isNonNull} from '../../lib/preconditions';
import {FlowResultsLocalStore} from '../../store/flow_results_local_store';
import {FlowArgsViewData} from '../flow_args_view/flow_args_view';

import {ColorScheme} from './helpers/result_accordion';
import {
  FLOW_DETAILS_DEFAULT_PLUGIN,
  FLOW_DETAILS_PLUGIN_REGISTRY,
} from './plugin_registry';

/** Enum of Actions that can be triggered in the Flow Context Menu. */
export enum FlowMenuAction {
  NONE = 0,
  CANCEL,
  DUPLICATE,
  CREATE_HUNT,
  START_VIA_API,
  DEBUG,
}

/**
 * Component that displays detailed information about a flow.
 */
@Component({
  standalone: false,
  selector: 'flow-details',
  templateUrl: './flow_details.ng.html',
  styleUrls: ['./flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class FlowDetails implements OnChanges {
  readonly ButtonType = ButtonType;
  constructor(private readonly clipboard: Clipboard) {}

  readonly colorScheme = ColorScheme;

  private detailsComponent: ComponentRef<FlowDetailsPlugin> | undefined;

  flowState = FlowState;
  flowMenuAction = FlowMenuAction;

  private readonly flow$ = new BehaviorSubject<Flow | null>(null);
  private readonly flowDescriptor$ = new BehaviorSubject<FlowDescriptor | null>(
    null,
  );
  private readonly webAuthType$ = new BehaviorSubject<string | null>(null);
  private readonly exportCommandPrefix$ = new BehaviorSubject<string | null>(
    null,
  );

  readonly flowArgsViewData$: Observable<FlowArgsViewData | null> =
    combineLatest([this.flow$, this.flowDescriptor$]).pipe(
      map(([flow, flowDescriptor]) => {
        if (!flow || !flowDescriptor) {
          return null;
        }
        return {
          flowDescriptor,
          flowArgs: this.flow!.args as {},
        };
      }),
      startWith(null),
    );

  readonly flowTitle$: Observable<string | undefined> = combineLatest([
    this.flow$,
    this.flowDescriptor$,
  ]).pipe(map(([flow, fd]) => getFlowTitleFromFlow(flow, fd)));

  /**
   * Start flow API Request that is copied to clipboard.
   */
  startFlowRequest$: Observable<string | null> = combineLatest([
    this.flow$,
    this.webAuthType$,
  ]).pipe(
    map(([flow, webAuthType]) => {
      if (!flow) {
        return null;
      }
      return this.createFlowRequestStr(flow);
    }),
  );

  /** Creates a API request to start a given flow. */
  createFlowRequestStr(flow: Flow) {
    return `CSRFTOKEN='curl ${window.location.origin} -o /dev/null -s -c - | grep csrftoken  | cut -f 7' \\
  curl -X POST -H "Content-Type: application/json" -H "X-CSRFToken: $CSRFTOKEN" \\
  ${window.location.origin}/api/v2/clients/${flow.clientId}/flows -d @- << EOF
${JSON.stringify({flow: {args: flow.args, name: flow.name}}, null, 2)}
EOF`;
  }

  /**
   * Flow list entry to display.
   */

  flowLink$: Observable<string | null> = this.flow$.pipe(
    map((flow) => makeFlowLink(flow?.clientId, flow?.flowId)),
  );

  /**
   * WebAuthType to use for create flow API requests.
   */
  @Input()
  set webAuthType(webAuthType: string | null) {
    this.webAuthType$.next(webAuthType ?? null);
  }

  get webAuthType() {
    return this.webAuthType$.value;
  }

  /**
   * exportCommandPrefix to .
   */
  @Input()
  set exportCommandPrefix(exportCommandPrefix: string | null) {
    this.exportCommandPrefix$.next(exportCommandPrefix ?? null);
  }

  get exportCommandPrefix() {
    return this.exportCommandPrefix$.value;
  }

  @Input()
  set flow(flow: Flow | null | undefined) {
    this.flow$.next(flow ?? null);
  }

  get flow() {
    return this.flow$.value;
  }

  /**
   * Flow descriptor of the flow to display. May be undefined if user is not
   * allowed to start this flow or flow class has been deprecated/removed.
   */
  @Input()
  set flowDescriptor(desc: FlowDescriptor | null | undefined) {
    this.flowDescriptor$.next(desc ?? null);
  }

  get flowDescriptor() {
    return this.flowDescriptor$.value;
  }

  /**
   * Whether show "Create a hunt" in the menu.
   */
  @Input() showContextMenu = true;

  /**
   * Event that is triggered when a flow context menu action is selected.
   */
  @Output() readonly menuActionTriggered = new EventEmitter<FlowMenuAction>();

  @ViewChild('detailsContainer', {read: ViewContainerRef, static: true})
  detailsContainer!: ViewContainerRef;

  ngOnChanges(changes: SimpleChanges) {
    if (!this.flow) {
      this.detailsContainer.clear();
      return;
    }

    let componentClass =
      FLOW_DETAILS_PLUGIN_REGISTRY[this.flow.name as FlowType];

    // As fallback for flows without details plugin and flows that do not report
    // resultCount metadata, show a default view that links to the old UI.
    if (!componentClass || this.flow.resultCounts === undefined) {
      componentClass = FLOW_DETAILS_DEFAULT_PLUGIN;
    }

    // Only recreate the component if the component class has changed.
    if (componentClass !== this.detailsComponent?.instance.constructor) {
      this.detailsContainer.clear();
      this.detailsComponent =
        this.detailsContainer.createComponent(componentClass);
    }

    if (!this.detailsComponent) {
      throw new Error(
        'detailsComponentInstance was expected to be defined at this point.',
      );
    }

    this.detailsComponent.instance.exportCommandPrefix =
      this.exportCommandPrefix ?? '';
    this.detailsComponent.instance.flow = this.flow;
    // If the input bindings are set programmatically and not through a
    // template, and you have OnPush strategy, then change detection won't
    // trigger. We have to explicitly mark the dynamically created component
    // for changes checking.
    //
    // For more context, see this excellent article:
    // https://netbasal.com/things-worth-knowing-about-dynamic-components-in-angular-166ce136b3eb
    // "When we dynamically create a component and insert it into the view by
    // using a ViewContainerRef, Angular will invoke each one of the
    // lifecycle hooks except for the ngOnChanges() hook.
    // The reason for that is the ngOnChanges hook isn’t called when inputs
    // are set programmatically only by the view."
    // Doing this.detailsComponent.changeDetectorRef.detectChanges() won't
    // help since, this way "we’re running detectChanges() on the host view,
    // not on the component itself and because we’re in onPush and setting
    // the input programmatically from Angular perspective nothing has changed."
    this.detailsComponent.injector.get(ChangeDetectorRef).markForCheck();
  }

  triggerMenuEvent(action: FlowMenuAction) {
    this.menuActionTriggered.emit(action);
  }

  get resultDescription() {
    return this.flow
      ? this.detailsComponent?.instance?.getResultDescription(this.flow)
      : undefined;
  }

  get exportMenuItems() {
    return this.flow?.state === FlowState.FINISHED
      ? this.detailsComponent?.instance?.getExportMenuItems(
          this.flow,
          this.exportCommandPrefix ?? '',
        )
      : undefined;
  }

  get hasResults() {
    return isNonNull(this.flow?.resultCounts?.find((rc) => rc.count > 0));
  }

  trackExportMenuItem(index: number, entry: ExportMenuItem) {
    return entry.title;
  }

  copyToClipboard(str: string) {
    if (str !== null) {
      this.clipboard.copy(str);
    }
  }
}
