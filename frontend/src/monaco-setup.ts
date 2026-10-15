/**
 * Настройка Monaco для Vite: editor worker через ?worker-импорт
 * и передача локального инстанса в @monaco-editor/react (без загрузки с CDN).
 */
import * as monaco from 'monaco-editor';
import { loader } from '@monaco-editor/react';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

(self as any).MonacoEnvironment = {
  getWorker: () => new editorWorker(),
};

loader.config({ monaco });
