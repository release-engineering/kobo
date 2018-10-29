from mock import Mock, PropertyMock

from kobo.hub.xmlrpc import worker
from kobo.xmlrpc import encode_xmlrpc_chunks_iterator


class _RequestMock(object):

    def __init__(self, worker_instance):
        self.worker = worker_instance
        self.user = Mock()
        self.user.is_authenticated.return_value = True
        type(self.user).username = PropertyMock(return_value='mockuser')


class RpcServiceMock(object):
    '''
    RpcServiceMock implements all XML-RPC methods.
    '''

    def __init__(self, worker_instance):
        self.worker = worker_instance
        self._request = _RequestMock(worker_instance)

    def get_worker_info(self):
        return worker.get_worker_info(self._request)

    def get_worker_id(self):
        return worker.get_worker_id(self._request)

    def get_worker_tasks(self):
        return worker.get_worker_tasks(self._request)

    def get_task(self, task_id):
        return worker.get_task(self._request, task_id)

    def get_task_no_verify(self, task_id):
        return worker.get_task_no_verify(self._request, task_id)

    def interrupt_tasks(self, task_list):
        return worker.interrupt_tasks(self._request, task_list)

    def timeout_tasks(self, task_list):
        return worker.timeout_tasks(self._request, task_list)

    def assign_task(self, task_id):
        return worker.assign_task(self._request, task_id)

    def open_task(self, task_id):
        return worker.open_task(self._request, task_id)

    def close_task(self, task_id, task_result):
        return worker.close_task(self._request, task_id, task_result)

    def cancel_task(self, task_id):
        return worker.cancel_task(self._request, task_id)

    def fail_task(self, task_id, task_result):
        return worker.fail_task(self._request, task_id, task_result)

    def set_task_weight(self, task_id, weight):
        return worker.set_task_weight(self._request, task_id, weight)

    def update_worker(self, enabled, ready, task_count):
        return worker.update_worker(self._request, enabled, ready, task_count)

    def get_tasks_to_assign(self):
        return worker.get_tasks_to_assign(self._request, )

    def get_awaited_tasks(self, awaited_task_list):
        return worker.get_awaited_tasks(self._request, awaited_task_list)

    def create_subtask(self, label, method, args, parent_id):
        return worker.create_subtask(self._request, label, method, args, parent_id)

    def wait(self, task_id, child_list=None):
        return worker.wait(self._request, task_id, child_list)

    def check_wait(self, task_id, child_list=None):
        return worker.check_wait(self._request, task_id, child_list)

    def upload_task_log(self, task_id, relative_path, mode, chunk_start,
                        chunk_len, chunk_checksum, encoded_chunk):
        return worker.upload_task_log(self._request, task_id, relative_path, mode, chunk_start,
                                      chunk_len, chunk_checksum, encoded_chunk)


class HubProxyMock(object):
    ''' Mock for kobo.client.HubProxy '''

    def __init__(self, conf, **kwargs):
        if 'worker' in kwargs:
            self.worker = kwargs.get('worker')
        else:
            self.worker = conf.get('worker')

        if self.worker is None:
            raise Exception('Missing worker argument')

    def upload_file(self, file_name, target_dir):
        # TODO: This should be implemented as in the original class.
        pass

    def upload_task_log(self, file_obj, task_id, remote_file_name, append=True, mode=0o644):
        # TODO: This should be implemented as in the original class.
        pass
