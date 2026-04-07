// Redux store setup for Kepler.gl.
//
// Kepler dispatches thunks & tasks through react-palm's taskMiddleware —
// without it, certain async actions (like tile loading) silently no-op.

import { applyMiddleware, combineReducers, compose, createStore } from 'redux';
import { taskMiddleware } from 'react-palm/tasks';
import keplerGlReducer, { enhanceReduxMiddleware } from '@kepler.gl/reducers';

const customizedKeplerReducer = keplerGlReducer.initialState({
  uiState: {
    readOnly: false,
    currentModal: null
  }
});

const reducers = combineReducers({
  keplerGl: customizedKeplerReducer
});

const middlewares = enhanceReduxMiddleware([taskMiddleware]);
const enhancers = applyMiddleware(...middlewares);

export const store = createStore(reducers, {}, compose(enhancers));
export type RootState = ReturnType<typeof reducers>;
