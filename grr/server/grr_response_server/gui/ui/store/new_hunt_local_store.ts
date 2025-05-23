import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, Observable, of} from 'rxjs';
import {
  filter,
  map,
  shareReplay,
  startWith,
  switchMap,
  takeWhile,
  tap,
  withLatestFrom,
} from 'rxjs/operators';

import {
  AdminUIHuntConfig,
  ApiHunt,
  ForemanClientRuleSet,
  ForemanClientRuleType,
  OutputPluginDescriptor,
} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatusType, trackRequest} from '../lib/api/track_request';
import {translateFlow} from '../lib/api_translation/flow';
import {
  translateHunt,
  translateSafetyLimits,
} from '../lib/api_translation/hunt';
import {FlowWithDescriptor} from '../lib/models/flow';
import {Hunt, HuntPresubmit, SafetyLimits} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';

interface OriginalFlowRef {
  readonly clientId: string;
  readonly flowId: string;
}

interface NewHuntState {
  readonly originalFlowRef?: OriginalFlowRef;
  readonly originalHuntId?: string;
  readonly huntId?: string;
  readonly currentDescription?: string;
}

/** ComponentStore implementation used by the NewHuntLocalStore. */
class NewHuntComponentStore extends ComponentStore<NewHuntState> {
  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    super({});
    this.flowWithDescriptor$ = combineLatest([
      this.originalFlowRef$,
      this.hasClientAccess$,
      this.configGlobalStore.flowDescriptors$,
    ]).pipe(
      switchMap(([flowRef, hasAccess, fds]) => {
        return flowRef && hasAccess
          ? this.httpApiService
              .fetchFlow(flowRef.clientId, flowRef.flowId)
              .pipe(
                map((apiFlow) => {
                  if (apiFlow) {
                    const type = apiFlow.args?.['@type'];
                    return {
                      flow: translateFlow(apiFlow),
                      descriptor: fds.get(apiFlow.name ?? ''),
                      flowArgType: typeof type === 'string' ? type : undefined,
                    };
                  }
                  return null;
                }),
              )
          : of(null);
      }),
      startWith(null),
    );
    this.defaultSafetyLimits$ = this.configGlobalStore.uiConfig$.pipe(
      map((config) => config.defaultHuntRunnerArgs),
      filter(isNonNull),
      map(translateSafetyLimits),
    );
    this.defaultClientRuleSet$ = this.configGlobalStore.uiConfig$.pipe(
      map((config) => config.defaultHuntRunnerArgs),
      filter(isNonNull),
      map((hra) => {
        if (!hra.clientRuleSet) {
          return {
            rules: [
              // Add an extra OS rule at the beginning of the rules list.
              {ruleType: ForemanClientRuleType.OS},
            ],
          };
        }

        return {
          ...hra.clientRuleSet,
          rules: [
            // Add an extra OS rule at the beginning of the rules list.
            {ruleType: ForemanClientRuleType.OS},
            ...(hra.clientRuleSet.rules ?? []),
          ],
        };
      }),
    );
    this.presubmitOptions$ = combineLatest([
      this.currentDescription$,
      this.configGlobalStore.uiConfig$.pipe(map((config) => config.huntConfig)),
    ]).pipe(
      map(([description, huntConfig]) => {
        if (!huntConfig?.presubmitCheckWithSkipTag) {
          return undefined;
        }

        const skipTag = huntConfig.presubmitCheckWithSkipTag ?? '';
        if ((description ?? '').includes(skipTag)) return undefined;

        return this.buildHuntPresubmitClientRuleSet(huntConfig, skipTag);
      }),
      shareReplay({bufferSize: 1, refCount: true}),
    );
    this.runHunt = this.effect<{
      description: string;
      safetyLimits: SafetyLimits;
      rules: ForemanClientRuleSet;
      outputPlugins: readonly OutputPluginDescriptor[];
    }>((obs$) =>
      obs$.pipe(
        withLatestFrom(
          this.flowWithDescriptor$,
          this.originalHunt$,
          this.state$,
        ),
        switchMap(([opts, flowWithDescriptors, originalHunt, state]) => {
          return trackRequest(
            this.httpApiService.createHunt(
              opts.description,
              flowWithDescriptors,
              originalHunt,
              opts.safetyLimits,
              opts.rules,
              opts.outputPlugins,
              state.originalHuntId,
            ),
          );
        }),
        tap((status) => {
          if (status.status === RequestStatusType.SUCCESS) {
            this.updateHuntId(status.data?.huntId);
          }
        }),
      ),
    );
    this.updateHuntId = this.updater<string | undefined>((state, huntId) => ({
      ...state,
      huntId,
    }));
    this.huntId$ = this.select((state) => state.huntId);
  }

  /** Reducer updating the store and setting the clientId and flowId. */
  readonly selectOriginalFlow = this.updater<OriginalFlowRef>(
    (state, originalFlowRef) => ({...state, originalFlowRef}),
  );
  readonly selectOriginalHunt = this.updater<string>(
    (state, originalHuntId) => ({...state, originalHuntId}),
  );
  readonly setCurrentDescription = this.updater<string>(
    (state, currentDescription) => ({...state, currentDescription}),
  );

  private readonly originalFlowRef$: Observable<OriginalFlowRef | undefined> =
    this.select((state) => state.originalFlowRef);
  private readonly originalHuntId$: Observable<string> = this.select(
    (state) => state.originalHuntId,
  ).pipe(filter(isNonNull), shareReplay({bufferSize: 1, refCount: true}));
  private readonly currentDescription$: Observable<string | undefined> =
    this.select((state) => state.currentDescription);

  readonly originalHunt$: Observable<Hunt | null> = this.originalHuntId$.pipe(
    switchMap((huntId) => {
      return this.httpApiService.fetchHunt(huntId).pipe(
        map((hunt: ApiHunt): Hunt => {
          const flowRef = hunt?.originalObject?.flowReference;
          if (flowRef && flowRef.clientId && flowRef.flowId) {
            this.selectOriginalFlow({
              clientId: flowRef.clientId,
              flowId: flowRef.flowId,
            });
          }

          return translateHunt(hunt);
        }),
      );
    }),
    startWith(null),
    shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly hasClientAccess$: Observable<boolean | undefined> =
    this.originalFlowRef$.pipe(
      switchMap((flowRef) =>
        flowRef && flowRef.clientId
          ? this.httpApiService
              .subscribeToVerifyClientAccess(flowRef.clientId)
              .pipe(
                takeWhile((hasAccess) => !hasAccess, true),
                startWith(undefined),
              )
          : of(undefined),
      ),
      shareReplay({bufferSize: 1, refCount: true}),
    );

  readonly flowWithDescriptor$: Observable<FlowWithDescriptor | null>;

  readonly defaultSafetyLimits$: Observable<SafetyLimits>;

  readonly defaultClientRuleSet$: Observable<ForemanClientRuleSet>;

  buildHuntPresubmitClientRuleSet(
    huntConfig: AdminUIHuntConfig,
    skipTag: string,
  ): HuntPresubmit {
    if (
      !huntConfig.presubmitCheckWithSkipTag ||
      !huntConfig.defaultExcludeLabels
    ) {
      return {} as HuntPresubmit;
    }

    const message = `${huntConfig.presubmitWarningMessage}\nYou
          **MUST match all** the conditions and
          **MUST exclude** the following labels from your fleet collection:
          **[${huntConfig.defaultExcludeLabels.join(', ')}]**
          or add a _'${skipTag}=<reason>'_ tag to the description.`;

    return {
      markdownText: message,
      expectedExcludedLabels: [...huntConfig.defaultExcludeLabels],
    };
  }

  readonly presubmitOptions$: Observable<HuntPresubmit | undefined>;

  /** An effect to run a hunt */
  readonly runHunt;

  private readonly updateHuntId;

  readonly huntId$: Observable<string | undefined>;
}

/** LocalStore for new hunt related API calls. */
@Injectable()
export class NewHuntLocalStore {
  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    this.store = new NewHuntComponentStore(
      this.httpApiService,
      this.configGlobalStore,
    );
    this.defaultSafetyLimits$ = this.store.defaultSafetyLimits$;
    this.defaultClientRuleSet$ = this.store.defaultClientRuleSet$;
    this.presubmitOptions$ = this.store.presubmitOptions$;
    this.huntId$ = this.store.huntId$;
    this.flowWithDescriptor$ = this.store.flowWithDescriptor$;
    this.originalHunt$ = this.store.originalHunt$;
  }

  private readonly store;
  /** Selects a flow with a given parameters. */
  selectOriginalFlow(clientId: string, flowId: string): void {
    this.store.selectOriginalFlow({clientId, flowId});
  }
  selectOriginalHunt(huntId: string): void {
    this.store.selectOriginalHunt(huntId);
  }
  setCurrentDescription(description: string): void {
    this.store.setCurrentDescription(description);
  }

  runHunt(
    description: string,
    safetyLimits: SafetyLimits,
    rules: ForemanClientRuleSet,
    outputPlugins: readonly OutputPluginDescriptor[],
  ): void {
    this.store.runHunt({description, safetyLimits, rules, outputPlugins});
  }

  readonly defaultSafetyLimits$;
  readonly defaultClientRuleSet$;
  readonly presubmitOptions$;
  readonly huntId$;
  readonly flowWithDescriptor$;
  readonly originalHunt$;
}
