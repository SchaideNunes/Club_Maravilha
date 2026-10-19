import { describe, expect, it, vi } from 'vitest';
import { createShutdownHandler } from './shutdown.js';

describe('createShutdownHandler', () => {
  it('executa service.stop() primeiro, server.close() em seguida, aguarda saveCreds e finaliza com exit(0)', async () => {
    const callOrder: string[] = [];

    const fakeService = {
      stop: vi.fn().mockImplementation(() => {
        callOrder.push('service.stop');
      }),
    };

    const fakeServer = {
      close: vi.fn().mockImplementation((cb?: (err?: unknown) => void) => {
        callOrder.push('server.close');
        cb?.();
      }),
    };

    const exitMock = vi.fn().mockImplementation((code?: number) => {
      callOrder.push(`exit(${code})`);
    });

    const shutdown = createShutdownHandler(
      fakeService,
      fakeServer,
      exitMock,
      50 // aguardo reduzido de saveCreds para o teste unitário
    );

    await shutdown();

    expect(callOrder).toEqual([
      'service.stop',
      'server.close',
      'exit(0)',
    ]);

    expect(fakeService.stop).toHaveBeenCalledTimes(1);
    expect(fakeServer.close).toHaveBeenCalledTimes(1);
    expect(exitMock).toHaveBeenCalledWith(0);
  });

  it('é idempotente: chamadas concorrentes/duplicadas executam o encerramento uma única vez', async () => {
    const fakeService = {
      stop: vi.fn(),
    };

    const fakeServer = {
      close: vi.fn().mockImplementation((cb?: (err?: unknown) => void) => {
        setTimeout(cb ?? (() => {}), 10);
      }),
    };

    const exitMock = vi.fn();

    const shutdown = createShutdownHandler(
      fakeService,
      fakeServer,
      exitMock,
      10
    );

    // Duas chamadas simultâneas
    await Promise.all([shutdown(), shutdown()]);

    expect(fakeService.stop).toHaveBeenCalledTimes(1);
    expect(fakeServer.close).toHaveBeenCalledTimes(1);
    expect(exitMock).toHaveBeenCalledTimes(1);
  });
});
