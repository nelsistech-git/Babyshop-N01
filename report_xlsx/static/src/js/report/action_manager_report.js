/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {session} from "@web/session";
import {useService} from '@web/core/utils/misc';
import {DialogProvider} from '@web/core/utils/misc';
const {Component} = owl

class CustomActionManager extends Component {
    setup() {
        const actionManager = useService('actionManager');
        actionManager.include({
            _downloadReportXLSX: function (url, actions) {
                var self = this;
                DialogProvider.blockUI();
                var type = "xlsx";
                var cloned_action = _.clone(actions);
                var new_url = url;

                if (
                    _.isUndefined(cloned_action.data) ||
                    _.isNull(cloned_action.data) ||
                    (_.isObject(cloned_action.data) && _.isEmpty(cloned_action.data))
                ) {
                    if (cloned_action.context.active_ids) {
                        new_url += "/" + cloned_action.context.active_ids.join(",");
                    }
                } else {
                    new_url +=
                        "?options=" +
                        encodeURIComponent(JSON.stringify(cloned_action.data));
                    new_url +=
                        "&context=" +
                        encodeURIComponent(JSON.stringify(cloned_action.context));
                }

                return new Promise(function (resolve, reject) {
                    var blocked = !session.get_file({
                        url: new_url,
                        data: {
                            data: JSON.stringify([new_url, type]),
                        },
                        success: resolve,
                        error: (error) => {
                            self.call("crash_manager", "rpc_error", error);
                            reject();
                        },
                        complete: DialogProvider.unblockUI,
                    });
                    if (blocked) {
                        var message = _t(
                            "A popup window with your report was blocked. You " +
                            "may need to change your browser settings to allow " +
                            "popup windows for this page."
                        );
                        this.do_warn(_t("Warning"), message, true);
                    }
                });
            },

            _triggerDownload: function (action, options, type) {
                var self = this;
                var reportUrls = this._makeReportUrls(action);
                if (type === "xlsx") {
                    return this._downloadReportXLSX(reportUrls[type], action).then(
                        function () {
                            if (action.close_on_report_download) {
                                var closeAction = {type: "ir.actions.act_window_close"};
                                return self.doAction(
                                    closeAction,
                                    _.pick(options, "on_close")
                                );
                            }
                            return options.on_close();
                        }
                    );
                }
                return this._super.apply(this, arguments);
            },

            _makeReportUrls: function (action) {
                var reportUrls = this._super.apply(this, arguments);
                reportUrls.xlsx = "/report/xlsx/" + action.report_name;
                return reportUrls;
            },

            _executeReportAction: function (action, options) {
                var self = this;
                if (action.report_type === "xlsx") {
                    return self._triggerDownload(action, options, "xlsx");
                }
                return this._super.apply(this, arguments);
            },
        })
    }
}

