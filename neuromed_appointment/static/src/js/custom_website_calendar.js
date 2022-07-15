odoo.define('appointment.custom_select_appointment_type', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var WebsiteCalendarSelect = publicWidget.registry.appointmentTypeSelect;
    var appointmentSlotSelect = publicWidget.registry.appointmentSlotSelect;

    appointmentSlotSelect.include({
        xmlDependencies: ['/appointment/static/src/xml/calendar_appointment_slots.xml', '/neuromed_appointment/static/src/xml/calendar_appointment_slots.xml',],

        _onClickDaySlot: function (ev) {
            var res = this._super.apply(this, arguments);
            this.$('.o_slot_selected').removeClass('o_slot_selected');
            this.$(ev.currentTarget).addClass('o_slot_selected');
            const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
            const appointmentTypeIDs = this.$("input[name='filter_appointment_type_ids']").val();
            const slotDate = this.$(ev.currentTarget.firstElementChild).attr('id');
            const slots = JSON.parse(this.$(ev.currentTarget).find('div')[0].dataset['availableSlots']);
            const service_id = this.$("input[name='service_id']").val();
            const resource_id = this.$("input[name='resource_id']").val();
            const location_id = this.$("input[name='location_id']").val();
            const crm_id = this.$("input[name='crm_id']").val();

            let $slotsList = this.$('#slotsList').empty();
            $(qweb.render('appointment.slots_list', {
                slotDate: moment(slotDate).format("dddd D MMMM"),
                slots: slots,
                appointment_type_id: appointmentTypeID,
                filter_appointment_type_ids: appointmentTypeIDs,
                service_id: service_id,
                resource_id: resource_id,
                location_id: location_id,
                crm_id: crm_id,
            })).appendTo($slotsList);
            return res;
        },

        _onRefresh: function (ev) {
            var res = this._super.apply(this, arguments);
            if (this.$("#slots_availabilities")[0]) {
                var self = this;
                const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
                const employeeID = this.$("#slots_form select[name='employee_id']").val();
                const timezone = this.$("select[name='timezone']").val();
                const service_id = this.$("input[name='service_id']").val();
                const resource_id = this.$("input[name='resource_id']").val();
                const location_id = this.$("input[name='location_id']").val();
                const crm_id = this.$("input[name='crm_id']").val();
                this._rpc({
                    route: `/calendar/${appointmentTypeID}/update_available_slots`,
                    params: {
                        employee_id: employeeID,
                        timezone: timezone,
                        resource_id : resource_id,
                        service_id : service_id,
                        location_id : location_id,
                        crm_id : crm_id,
                    },
                }).then(function (data) {
                    if (data) {
                        self.$("#slots_availabilities").replaceWith(data);
                    }
                });
            }
            return res;
        },
    });

    WebsiteCalendarSelect.include({
        events: _.extend({}, WebsiteCalendarSelect.prototype.events, {
            'change #calendarType': '_onChangeAppointmentType',
            'change #resource': '_onChangeResource',
            'change #locations': '_onChangeLocation',
            'change #services': '_onChangeService',
        }),
        init: function () {
            this._super.apply(this, arguments);
            this.appointment_form = $('.o_website_appointment_form');
            this.appointment_form.find('button[type="submit"]').hide();
            this.resource_field = this.appointment_form.find('#resource');
            this.location_field = this.appointment_form.find('#locations');
            this.service_field = this.appointment_form.find('#services');
            this._display_appoint_btn();
        },
        _onChangeAppointmentType: async function (ev) {
            ev.preventDefault();
            var type_id = parseInt(this.appointment_form.find('#calendarType option:selected').val());
            var self = this;
            await this._rpc({
                route: "/calendar/get_all",
                params: {
                    type_id: type_id,
                },
            }).then(function (data) {
                if (data.resources.length) {
                    self.resource_field.find('option:not(:first)').remove();
                    _.each(data.resources, function (x) {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                        self.resource_field.append(opt);
                    });
                }
                if (data.locations.length) {
                    self.location_field.find('option:not(:first)').remove();
                    _.each(data.locations, function (x) {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                        self.location_field.append(opt);
                    });
                }
                if (data.services.length) {
                    self.service_field.find('option:not(:first)').remove();
                    _.each(data.services, function (x) {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                        self.service_field.append(opt);
                    });
                }
            });
        },

        _onChangeResource: async function (ev) {
            ev.preventDefault();
            var type_id = parseInt(this.appointment_form.find('#calendarType option:selected').val());
            var res_id = parseInt($(ev.currentTarget).find(':selected').val());
            var location_id = parseInt(this.appointment_form.find('#locations option:selected').val());
            var service_id = parseInt(this.appointment_form.find('#services option:selected').val());
            var self = this;
            if (res_id) {
                await this._rpc({
                    route: "/calendar/get_locations_services_by_resource",
                    params: {
                        type_id: type_id,
                        res_id: res_id
                    },
                }).then(function (data) {
                    if (data.locations.length) {
                        self.location_field.find('option:not(:first)').remove();
                        _.each(data.locations, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', location_id == x[0])
                            self.location_field.append(opt);
                        });
                    }
                    if (data.services.length) {
                        self.service_field.find('option:not(:first)').remove();
                        _.each(data.services, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', service_id == x[0])
                            self.service_field.append(opt);
                        });
                    }
                });
            }
            this._display_appoint_btn();
        },

        _onChangeLocation: async function (ev) {
            ev.preventDefault();
            var type_id = parseInt(this.appointment_form.find('#calendarType option:selected').val());
            var location_id = parseInt($(ev.currentTarget).find(':selected').val());
            var res_id = parseInt(this.appointment_form.find('#resource option:selected').val());
            var service_id = parseInt(this.appointment_form.find('#services option:selected').val());
            var self = this;
            if (location_id) {
                await this._rpc({
                    route: "/calendar/get_resources_services_by_location",
                    params: {
                        type_id: type_id,
                        location_id: location_id
                    },
                }).then(function (data) {
                    if (data.resources.length) {
                        self.resource_field.find('option:not(:first)').remove();
                        _.each(data.resources, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', res_id == x[0])
                            self.resource_field.append(opt);
                        });
                    }
                    if (data.services.length) {
                        self.service_field.find('option:not(:first)').remove();
                        _.each(data.services, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', service_id == x[0])
                            self.service_field.append(opt);
                        });
                    }
                });
            }
            this._display_appoint_btn();
        },

        _onChangeService: async function (ev) {
            ev.preventDefault();
            var type_id = parseInt(this.appointment_form.find('#calendarType option:selected').val());
            var service_id = parseInt($(ev.currentTarget).find(':selected').val());
            var res_id = parseInt(this.appointment_form.find('#resource option:selected').val());
            var location_id = parseInt(this.appointment_form.find('#locations option:selected').val());
            var self = this;
            if (service_id) {
                await this._rpc({
                    route: "/calendar/get_resources_locations_by_service",
                    params: {
                        type_id: type_id,
                        service_id: service_id
                    },
                }).then(function (data) {
                    if (data.resources.length) {
                        self.resource_field.find('option:not(:first)').remove();
                        _.each(data.resources, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', res_id == x[0])
                            self.resource_field.append(opt);
                        });
                    }
                    if (data.locations.length) {
                        self.location_field.find('option:not(:first)').remove();
                        _.each(data.locations, function (x) {
                            var opt = $('<option>').text(x[1])
                                .attr('value', x[0])
                                .attr('selected', location_id == x[0])
                            self.location_field.append(opt);
                        });
                    }
                });
            }
            this._display_appoint_btn();
        },

        _display_appoint_btn: async function () {
            var type_id = parseInt(this.appointment_form.find('#calendarType option:selected').val());
            var location_id = parseInt(this.appointment_form.find('#locations option:selected').val());
            var res_id = parseInt(this.appointment_form.find('#resource option:selected').val());
            var service_id = parseInt(this.appointment_form.find('#services option:selected').val());
            var crm_id = parseInt(this.appointment_form.find('#crm_id').val());
            var self = this;
            await this._rpc({
                    route: "/calendar/get_accepting_reservation",
                    params: {
                        type_id: type_id,
                    },
                }).then(function (data) {
                    if (data && data.state) {
                        if (type_id && res_id && location_id && service_id && crm_id) {
                            self.appointment_form.find('button[type="submit"]').show();
                        } else {
                            self.appointment_form.find('button[type="submit"]').hide();
                        }
                    }
                    else
                    {
                        if (type_id && res_id && location_id && service_id) {
                            self.appointment_form.find('button[type="submit"]').show();
                        } else {
                            self.appointment_form.find('button[type="submit"]').hide();
                        }   
                    }
                });
        },
    });
});
